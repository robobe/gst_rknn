#include <gst/base/gstbasetransform.h>
#include <gst/video/video.h>
#include <rga/im2d.h>
#include <rknn_api.h>

#include <algorithm>
#include <array>
#include <cmath>
#include <cstring>
#include <fstream>
#include <memory>
#include <mutex>
#include <stdexcept>
#include <string>
#include <vector>

#ifndef PACKAGE
#define PACKAGE "rknnyolov8"
#endif

GST_DEBUG_CATEGORY_STATIC(yolov8_debug);
#define GST_CAT_DEFAULT yolov8_debug

namespace {
constexpr int kSide = 640;
constexpr std::array<int, 80> kCocoIds = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 27, 28, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 67, 70, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 84, 85, 86, 87, 88, 89, 90};

void require(int status, const std::string& operation) {
    if (status < 0) throw std::runtime_error(operation + " (RKNN " + std::to_string(status) + ')');
}

float half_to_float(uint16_t bits) {
    const uint32_t sign = uint32_t(bits & 0x8000) << 16;
    uint32_t exponent = (bits >> 10) & 0x1f, fraction = bits & 0x3ff;
    if (!exponent) {
        if (!fraction) { float value; std::memcpy(&value, &sign, sizeof(value)); return value; }
        while (!(fraction & 0x400)) { fraction <<= 1; --exponent; }
        ++exponent; fraction &= ~0x400;
    } else if (exponent == 31) { exponent = 255; }
    else exponent += 112;
    const uint32_t value_bits = sign | (exponent << 23) | (fraction << 13);
    float value; std::memcpy(&value, &value_bits, sizeof(value)); return value;
}

struct Tensor {
    rknn_tensor_attr attr{};
    rknn_tensor_mem* mem = nullptr;

    float value(size_t index) const {
        if (index >= attr.n_elems) throw std::runtime_error("RKNN tensor index out of range");
        switch (attr.type) {
        case RKNN_TENSOR_FLOAT32: return static_cast<const float*>(mem->virt_addr)[index];
        case RKNN_TENSOR_FLOAT16: return half_to_float(static_cast<const uint16_t*>(mem->virt_addr)[index]);
        case RKNN_TENSOR_INT8: return (static_cast<const int8_t*>(mem->virt_addr)[index] - attr.zp) * attr.scale;
        case RKNN_TENSOR_UINT8: return (static_cast<const uint8_t*>(mem->virt_addr)[index] - attr.zp) * attr.scale;
        default: throw std::runtime_error("unsupported RKNN output tensor type");
        }
    }
};

struct Detection { float left, top, right, bottom, confidence; int category; };

float overlap(const Detection& a, const Detection& b) {
    const float left = std::max(a.left, b.left), top = std::max(a.top, b.top);
    const float right = std::min(a.right, b.right), bottom = std::min(a.bottom, b.bottom);
    const float intersection = std::max(0.f, right - left) * std::max(0.f, bottom - top);
    const float area_a = std::max(0.f, a.right - a.left) * std::max(0.f, a.bottom - a.top);
    const float area_b = std::max(0.f, b.right - b.left) * std::max(0.f, b.bottom - b.top);
    return intersection / std::max(1e-6f, area_a + area_b - intersection);
}

class Model {
public:
    explicit Model(const std::string& path) {
        std::ifstream input(path, std::ios::binary | std::ios::ate);
        if (!input) throw std::runtime_error("cannot open model: " + path);
        const auto size = input.tellg();
        if (size <= 0 || size > UINT32_MAX) throw std::runtime_error("invalid model: " + path);
        std::vector<char> bytes(static_cast<size_t>(size)); input.seekg(0);
        if (!input.read(bytes.data(), size)) throw std::runtime_error("cannot read model: " + path);
        require(rknn_init(&context_, bytes.data(), static_cast<uint32_t>(bytes.size()), 0, nullptr), "load model");
        try {
            rknn_input_output_num count{};
            require(rknn_query(context_, RKNN_QUERY_IN_OUT_NUM, &count, sizeof(count)), "query model I/O");
            if (count.n_input != 1 || count.n_output != 9) throw std::runtime_error("expected YOLOv8 model with one input and nine outputs");
            rknn_tensor_attr input_attr{}; input_attr.index = 0;
            require(rknn_query(context_, RKNN_QUERY_INPUT_ATTR, &input_attr, sizeof(input_attr)), "query model input");
            input_attr.type = RKNN_TENSOR_UINT8; input_attr.fmt = RKNN_TENSOR_NHWC; input_attr.pass_through = 0;
            input_attr.size = kSide * kSide * 3; input_attr.w_stride = kSide; input_attr.h_stride = kSide;
            input_attr.size_with_stride = kSide * kSide * 3;
            input_ = allocate(input_attr);
            scratch_ = rknn_create_mem(context_, kSide * kSide * 3);
            if (!scratch_ || !scratch_->virt_addr) throw std::runtime_error("cannot allocate RKNN preprocessing memory");
            for (uint32_t index = 0; index < count.n_output; ++index) {
                Tensor tensor{}; tensor.attr.index = index;
                require(rknn_query(context_, RKNN_QUERY_OUTPUT_ATTR, &tensor.attr, sizeof(tensor.attr)), "query model output");
                tensor.attr.type = RKNN_TENSOR_FLOAT32;
                tensor.attr.fmt = RKNN_TENSOR_NCHW;
                tensor.attr.size = tensor.attr.n_elems * sizeof(float);
                tensor.attr.size_with_stride = tensor.attr.size;
                tensor.mem = allocate(tensor.attr); outputs_.push_back(tensor);
            }
            validate_outputs();
        } catch (...) { release(); throw; }
    }
    ~Model() { release(); }
    Model(const Model&) = delete;

    std::vector<Detection> detect(const uint8_t* pixels, int width, int height, int stride, bool& use_rga,
                                  float confidence_threshold, float nms_threshold, unsigned max_detections) {
        const float scale = std::min(float(kSide) / width, float(kSide) / height);
        const int resized_width = std::lround(width * scale), resized_height = std::lround(height * scale);
        const int left = (kSide - resized_width) / 2, top = (kSide - resized_height) / 2;
        preprocess(pixels, width, height, stride, resized_width, resized_height, left, top, use_rga);
        require(rknn_run(context_, nullptr), "run inference");
        for (const auto& output : outputs_) require(rknn_mem_sync(context_, output.mem, RKNN_MEMORY_SYNC_FROM_DEVICE), "sync output");
        std::vector<Detection> candidates;
        for (size_t group = 0; group < outputs_.size(); group += 3) decode(outputs_[group], outputs_[group + 1], candidates, confidence_threshold);
        for (auto& box : candidates) {
            box.left = std::clamp((box.left - left) / scale, 0.f, float(width));
            box.right = std::clamp((box.right - left) / scale, 0.f, float(width));
            box.top = std::clamp((box.top - top) / scale, 0.f, float(height));
            box.bottom = std::clamp((box.bottom - top) / scale, 0.f, float(height));
        }
        std::sort(candidates.begin(), candidates.end(), [](const Detection& a, const Detection& b) { return a.confidence > b.confidence; });
        std::vector<Detection> kept; kept.reserve(std::min<size_t>(max_detections, candidates.size()));
        for (const auto& candidate : candidates) {
            bool duplicate = false;
            for (const auto& selected : kept) if (candidate.category == selected.category && overlap(candidate, selected) > nms_threshold) { duplicate = true; break; }
            if (!duplicate) kept.push_back(candidate);
            if (kept.size() == max_detections) break;
        }
        return kept;
    }

private:
    rknn_tensor_mem* allocate(rknn_tensor_attr attr) {
        auto* memory = rknn_create_mem(context_, attr.size_with_stride ? attr.size_with_stride : attr.size);
        if (!memory || !memory->virt_addr) throw std::runtime_error("cannot allocate RKNN tensor memory");
        memories_.push_back(memory); require(rknn_set_io_mem(context_, memory, &attr), "bind RKNN tensor memory"); return memory;
    }
    void validate_outputs() const {
        for (size_t group = 0; group < outputs_.size(); group += 3) {
            const auto& box = outputs_[group].attr, &score = outputs_[group + 1].attr, &sum = outputs_[group + 2].attr;
            if (box.n_dims != 4 || score.n_dims != 4 || sum.n_dims != 4 || box.fmt != RKNN_TENSOR_NCHW || score.fmt != RKNN_TENSOR_NCHW || sum.fmt != RKNN_TENSOR_NCHW ||
                box.dims[0] != 1 || box.dims[1] != 64 || score.dims[0] != 1 || score.dims[1] != 80 || sum.dims[0] != 1 || sum.dims[1] != 1 ||
                box.dims[2] != score.dims[2] || box.dims[3] != score.dims[3] || box.dims[2] != sum.dims[2] || box.dims[3] != sum.dims[3])
                throw std::runtime_error("unexpected YOLOv8 output tensor layout");
        }
    }
    void preprocess(const uint8_t* source, int width, int height, int stride, int target_width, int target_height, int left, int top, bool& use_rga) {
        require(rknn_mem_sync(context_, input_, RKNN_MEMORY_SYNC_FROM_DEVICE), "sync input");
        std::memset(input_->virt_addr, 0, input_->size);
        if (use_rga) {
            auto source_handle = importbuffer_virtualaddr(const_cast<uint8_t*>(source), stride * height);
            auto scratch_handle = importbuffer_fd(scratch_->fd, scratch_->size);
            auto output_handle = importbuffer_fd(input_->fd, input_->size);
            const bool ok = source_handle && scratch_handle && output_handle &&
                imresize(wrapbuffer_handle(source_handle, width, height, RK_FORMAT_RGB_888, stride / 3, height),
                         wrapbuffer_handle(scratch_handle, target_width, target_height, RK_FORMAT_RGB_888, kSide, kSide)) == IM_STATUS_SUCCESS &&
                imtranslate(wrapbuffer_handle(scratch_handle, target_width, target_height, RK_FORMAT_RGB_888, kSide, kSide),
                            wrapbuffer_handle(output_handle, kSide, kSide, RK_FORMAT_RGB_888), left, top) == IM_STATUS_SUCCESS;
            if (source_handle) releasebuffer_handle(source_handle);
            if (scratch_handle) releasebuffer_handle(scratch_handle);
            if (output_handle) releasebuffer_handle(output_handle);
            if (ok) { require(rknn_mem_sync(context_, input_, RKNN_MEMORY_SYNC_TO_DEVICE), "sync RGA input"); return; }
            use_rga = false;
        }
        auto* destination = static_cast<uint8_t*>(input_->virt_addr);
        for (int y = 0; y < target_height; ++y) {
            const float source_y = (y + .5f) * height / target_height - .5f;
            const int y0 = std::clamp(int(std::floor(source_y)), 0, height - 1), y1 = std::min(y0 + 1, height - 1);
            const float fy = source_y - std::floor(source_y);
            for (int x = 0; x < target_width; ++x) {
                const float source_x = (x + .5f) * width / target_width - .5f;
                const int x0 = std::clamp(int(std::floor(source_x)), 0, width - 1), x1 = std::min(x0 + 1, width - 1);
                const float fx = source_x - std::floor(source_x);
                for (int channel = 0; channel < 3; ++channel) {
                    const float a = source[y0 * stride + x0 * 3 + channel] * (1 - fx) + source[y0 * stride + x1 * 3 + channel] * fx;
                    const float b = source[y1 * stride + x0 * 3 + channel] * (1 - fx) + source[y1 * stride + x1 * 3 + channel] * fx;
                    destination[(top + y) * kSide * 3 + (left + x) * 3 + channel] = std::lround(a * (1 - fy) + b * fy);
                }
            }
        }
        require(rknn_mem_sync(context_, input_, RKNN_MEMORY_SYNC_TO_DEVICE), "sync CPU input");
    }
    void decode(const Tensor& boxes, const Tensor& scores, std::vector<Detection>& output, float threshold) const {
        const int height = boxes.attr.dims[2], width = boxes.attr.dims[3], stride = kSide / width;
        for (int y = 0; y < height; ++y) for (int x = 0; x < width; ++x) {
            int label = 0; float score = scores.value(y * width + x);
            for (int category = 1; category < 80; ++category) { const float candidate = scores.value((category * height + y) * width + x); if (candidate > score) { score = candidate; label = category; } }
            if (score < threshold) continue;
            std::array<float, 4> distance{};
            for (int side = 0; side < 4; ++side) {
                float maximum = -INFINITY;
                for (int bin = 0; bin < 16; ++bin) maximum = std::max(maximum, boxes.value(((side * 16 + bin) * height + y) * width + x));
                float sum = 0, weighted = 0;
                for (int bin = 0; bin < 16; ++bin) { const float e = std::exp(boxes.value(((side * 16 + bin) * height + y) * width + x) - maximum); sum += e; weighted += e * bin; }
                distance[side] = weighted / sum;
            }
            output.push_back({(x + .5f - distance[0]) * stride, (y + .5f - distance[1]) * stride,
                              (x + .5f + distance[2]) * stride, (y + .5f + distance[3]) * stride,
                              score, kCocoIds[label]});
        }
    }
    void release() noexcept {
        if (scratch_) rknn_destroy_mem(context_, scratch_);
        for (auto* memory : memories_) rknn_destroy_mem(context_, memory);
        if (context_) rknn_destroy(context_);
        scratch_ = input_ = nullptr; memories_.clear(); context_ = 0;
    }
    rknn_context context_ = 0;
    rknn_tensor_mem* input_ = nullptr;
    rknn_tensor_mem* scratch_ = nullptr;
    std::vector<rknn_tensor_mem*> memories_;
    std::vector<Tensor> outputs_;
};

struct State {
    std::mutex mutex;
    std::string model, resize = "auto";
    float confidence = .25f, nms = .45f;
    guint max_detections = 100;
    bool started = false;
    GstVideoInfo info{};
    std::unique_ptr<Model> network;
};
} // namespace

typedef struct _GstRknnYoloV8 { GstBaseTransform parent; State* state; } GstRknnYoloV8;
typedef struct _GstRknnYoloV8Class { GstBaseTransformClass parent_class; } GstRknnYoloV8Class;
G_DEFINE_TYPE(GstRknnYoloV8, gst_rknn_yolov8, GST_TYPE_BASE_TRANSFORM)

enum { PROP_0, PROP_MODEL, PROP_CONFIDENCE, PROP_NMS, PROP_MAX_DETECTIONS, PROP_RESIZE };
static GstStaticPadTemplate sink_template = GST_STATIC_PAD_TEMPLATE("sink", GST_PAD_SINK, GST_PAD_ALWAYS, GST_STATIC_CAPS("video/x-raw,format=RGB,width=[10,16384],height=[10,16384],interlace-mode=progressive"));
static GstStaticPadTemplate src_template = GST_STATIC_PAD_TEMPLATE("src", GST_PAD_SRC, GST_PAD_ALWAYS, GST_STATIC_CAPS("video/x-raw,format=RGB,width=[10,16384],height=[10,16384],interlace-mode=progressive"));

static void set_property(GObject* object, guint property, const GValue* value, GParamSpec* spec) {
    auto* self = reinterpret_cast<GstRknnYoloV8*>(object); auto& state = *self->state; std::lock_guard<std::mutex> lock(state.mutex);
    if (state.started) { GST_WARNING_OBJECT(self, "%s can only change in NULL or READY", spec->name); return; }
    switch (property) {
    case PROP_MODEL: state.model = g_value_get_string(value) ? g_value_get_string(value) : ""; break;
    case PROP_CONFIDENCE: state.confidence = g_value_get_float(value); break;
    case PROP_NMS: state.nms = g_value_get_float(value); break;
    case PROP_MAX_DETECTIONS: state.max_detections = g_value_get_uint(value); break;
    case PROP_RESIZE: state.resize = g_value_get_string(value) ? g_value_get_string(value) : ""; break;
    default: G_OBJECT_WARN_INVALID_PROPERTY_ID(object, property, spec);
    }
}
static void get_property(GObject* object, guint property, GValue* value, GParamSpec* spec) {
    auto& state = *reinterpret_cast<GstRknnYoloV8*>(object)->state; std::lock_guard<std::mutex> lock(state.mutex);
    switch (property) {
    case PROP_MODEL: g_value_set_string(value, state.model.c_str()); break;
    case PROP_CONFIDENCE: g_value_set_float(value, state.confidence); break;
    case PROP_NMS: g_value_set_float(value, state.nms); break;
    case PROP_MAX_DETECTIONS: g_value_set_uint(value, state.max_detections); break;
    case PROP_RESIZE: g_value_set_string(value, state.resize.c_str()); break;
    default: G_OBJECT_WARN_INVALID_PROPERTY_ID(object, property, spec);
    }
}
static gboolean start(GstBaseTransform* base) {
    auto& state = *reinterpret_cast<GstRknnYoloV8*>(base)->state; std::lock_guard<std::mutex> lock(state.mutex);
    try {
        if (state.model.empty() || (state.resize != "auto" && state.resize != "cpu") || state.confidence < 0 || state.confidence > 1 || state.nms < 0 || state.nms > 1 || !state.max_detections)
            throw std::runtime_error("model is required; thresholds must be in [0,1], max-detections must be positive, resize must be auto or cpu");
        state.network = std::make_unique<Model>(state.model); state.started = true; return TRUE;
    } catch (const std::exception& error) { GST_ELEMENT_ERROR(base, RESOURCE, SETTINGS, ("Cannot start YOLOv8 detector"), ("%s", error.what())); return FALSE; }
}
static gboolean stop(GstBaseTransform* base) {
    auto& state = *reinterpret_cast<GstRknnYoloV8*>(base)->state; std::lock_guard<std::mutex> lock(state.mutex);
    state.network.reset(); state.started = false; return TRUE;
}
static gboolean set_caps(GstBaseTransform* base, GstCaps* input, GstCaps*) {
    auto& state = *reinterpret_cast<GstRknnYoloV8*>(base)->state; GstVideoInfo info;
    if (!gst_video_info_from_caps(&info, input) || GST_VIDEO_INFO_FORMAT(&info) != GST_VIDEO_FORMAT_RGB || GST_VIDEO_INFO_IS_INTERLACED(&info)) return FALSE;
    std::lock_guard<std::mutex> lock(state.mutex); state.info = info; return TRUE;
}
static GstFlowReturn transform_ip(GstBaseTransform* base, GstBuffer* buffer) {
    auto& state = *reinterpret_cast<GstRknnYoloV8*>(base)->state; GstVideoFrame frame{}; bool mapped = false;
    try {
        std::lock_guard<std::mutex> lock(state.mutex);
        if (!state.network || !gst_video_frame_map(&frame, &state.info, buffer, GST_MAP_READ)) throw std::runtime_error("cannot map RGB frame");
        mapped = true;
        bool use_rga = state.resize == "auto";
        const auto detections = state.network->detect(static_cast<const uint8_t*>(GST_VIDEO_FRAME_PLANE_DATA(&frame, 0)), GST_VIDEO_FRAME_WIDTH(&frame), GST_VIDEO_FRAME_HEIGHT(&frame), GST_VIDEO_FRAME_PLANE_STRIDE(&frame, 0), use_rga, state.confidence, state.nms, state.max_detections);
        gst_video_frame_unmap(&frame); mapped = false;
        if (!use_rga && state.resize == "auto") { state.resize = "cpu"; GST_WARNING_OBJECT(base, "RGA preprocessing failed; using CPU resize for this instance"); }
        for (const auto& box : detections) {
            const int x = std::clamp(int(std::floor(box.left)), 0, GST_VIDEO_INFO_WIDTH(&state.info));
            const int y = std::clamp(int(std::floor(box.top)), 0, GST_VIDEO_INFO_HEIGHT(&state.info));
            const int right = std::clamp(int(std::ceil(box.right)), 0, GST_VIDEO_INFO_WIDTH(&state.info));
            const int bottom = std::clamp(int(std::ceil(box.bottom)), 0, GST_VIDEO_INFO_HEIGHT(&state.info));
            if (right <= x || bottom <= y) continue;
            auto* roi = gst_buffer_add_video_region_of_interest_meta(buffer, "yolo8", x, y, right - x, bottom - y);
            if (!roi) throw std::runtime_error("cannot attach detection metadata");
            roi->id = box.category;
            gst_video_region_of_interest_meta_add_param(roi, gst_structure_new("yolo8", "confidence", G_TYPE_DOUBLE, double(box.confidence), nullptr));
        }
        return GST_FLOW_OK;
    } catch (const std::exception& error) {
        if (mapped) gst_video_frame_unmap(&frame);
        GST_ELEMENT_ERROR(base, STREAM, FAILED, ("YOLOv8 frame processing failed"), ("%s", error.what())); return GST_FLOW_ERROR;
    }
}
static void finalize(GObject* object) { delete reinterpret_cast<GstRknnYoloV8*>(object)->state; G_OBJECT_CLASS(gst_rknn_yolov8_parent_class)->finalize(object); }
static void gst_rknn_yolov8_class_init(GstRknnYoloV8Class* klass) {
    auto* object = G_OBJECT_CLASS(klass); auto* element = GST_ELEMENT_CLASS(klass); auto* transform = GST_BASE_TRANSFORM_CLASS(klass);
    object->set_property = set_property; object->get_property = get_property; object->finalize = finalize;
    const auto ready = GParamFlags(G_PARAM_READWRITE | G_PARAM_STATIC_STRINGS | GST_PARAM_MUTABLE_READY);
    g_object_class_install_property(object, PROP_MODEL, g_param_spec_string("model", "Model", "Required YOLOv8 RKNN model path", "", ready));
    g_object_class_install_property(object, PROP_CONFIDENCE, g_param_spec_float("confidence-threshold", "Confidence threshold", "Minimum class confidence", 0, 1, .25f, ready));
    g_object_class_install_property(object, PROP_NMS, g_param_spec_float("nms-iou-threshold", "NMS IoU threshold", "Same-class suppression IoU", 0, 1, .45f, ready));
    g_object_class_install_property(object, PROP_MAX_DETECTIONS, g_param_spec_uint("max-detections", "Maximum detections", "Maximum metadata records per frame", 1, 1000, 100, ready));
    g_object_class_install_property(object, PROP_RESIZE, g_param_spec_string("resize", "Resize", "auto: RGA with CPU fallback; cpu: CPU only", "auto", ready));
    gst_element_class_set_static_metadata(element, "RKNN YOLOv8 detector", "Filter/Metadata/Video", "Attaches COCO detection ROI metadata to RGB video", "gst-rknn");
    gst_element_class_add_static_pad_template(element, &sink_template); gst_element_class_add_static_pad_template(element, &src_template);
    transform->start = GST_DEBUG_FUNCPTR(start); transform->stop = GST_DEBUG_FUNCPTR(stop); transform->set_caps = GST_DEBUG_FUNCPTR(set_caps); transform->transform_ip = GST_DEBUG_FUNCPTR(transform_ip);
}
static void gst_rknn_yolov8_init(GstRknnYoloV8* self) { self->state = new State; gst_video_info_init(&self->state->info); gst_base_transform_set_in_place(GST_BASE_TRANSFORM(self), TRUE); }
static gboolean plugin_init(GstPlugin* plugin) { GST_DEBUG_CATEGORY_INIT(yolov8_debug, "rknnyolov8", 0, "RKNN YOLOv8 detector"); return gst_element_register(plugin, "rknnyolov8", GST_RANK_NONE, gst_rknn_yolov8_get_type()); }
GST_PLUGIN_DEFINE(GST_VERSION_MAJOR, GST_VERSION_MINOR, rknnyolov8, "RKNN YOLOv8 detection metadata", plugin_init, "1.0", "LGPL", "gst-rknn", "https://example.com")
