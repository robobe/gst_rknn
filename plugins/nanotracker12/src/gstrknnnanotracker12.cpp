#include <gst/base/gstbasetransform.h>
#include <gst/video/video.h>
#include <opencv2/imgproc.hpp>
#include <rga/im2d.h>
#include <rknn_api.h>

#include <algorithm>
#include <cmath>
#include <cstring>
#include <fstream>
#include <memory>
#include <mutex>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#ifndef PACKAGE
#define PACKAGE "rknnnanotracker12"
#endif

GST_DEBUG_CATEGORY_STATIC(nanotracker12_debug);
#define GST_CAT_DEFAULT nanotracker12_debug

namespace {
void require(int status, const char* what) {
    if (status < 0) throw std::runtime_error(std::string(what) + " (RKNN " + std::to_string(status) + ")");
}

cv::Rect2d roi_from_text(const std::string& text, int width, int height) {
    cv::Rect2d roi; char comma1, comma2, comma3; std::istringstream input(text);
    if (!(input >> roi.x >> comma1 >> roi.y >> comma2 >> roi.width >> comma3 >> roi.height) ||
        comma1 != ',' || comma2 != ',' || comma3 != ',' || !(input >> std::ws).eof() ||
        !std::isfinite(roi.x) || !std::isfinite(roi.y) || !std::isfinite(roi.width) || !std::isfinite(roi.height) ||
        roi.x < 0 || roi.y < 0 || roi.width < 1 || roi.height < 1 || roi.x + roi.width > width || roi.y + roi.height > height)
        throw std::runtime_error("roi must be x,y,width,height inside the frame");
    return roi;
}

float padded(float width, float height) {
    const float context = (width + height) * .5f;
    return std::sqrt((width + context) * (height + context));
}

struct Profile { float window, penalty, learning; };
Profile profile_for(const std::string& version) {
    if (version == "v1") return {.462f, .148f, .390f};
    if (version == "v2") return {.490f, .150f, .385f};
    throw std::runtime_error("model-version must be v1 or v2");
}

std::string file_for(const std::string& root, const std::string& version, const std::string& precision,
                     const char* name, bool head) {
    if (root.empty()) throw std::runtime_error("models-dir is required when enabled");
    std::string suffix;
    if (precision == "int8") suffix = "_int8";
    else if (precision == "int8-mmse") suffix = "_int8_mmse";
    else if (precision == "mixed" && head) suffix = "_int8";
    else if (precision != "fp16" && precision != "mixed") throw std::runtime_error("invalid precision");
    return root + "/" + version + "/rknn/" + name + suffix + ".rknn";
}

class Network {
public:
    explicit Network(const std::string& path) {
        std::ifstream input(path, std::ios::binary | std::ios::ate);
        if (!input) throw std::runtime_error("cannot open model: " + path);
        const auto size = input.tellg();
        if (size <= 0 || size > UINT32_MAX) throw std::runtime_error("invalid model: " + path);
        std::vector<char> data(static_cast<size_t>(size)); input.seekg(0);
        if (!input.read(data.data(), size)) throw std::runtime_error("cannot read model: " + path);
        require(rknn_init(&context_, data.data(), static_cast<uint32_t>(data.size()), 0, nullptr), "load model");
        try { require(rknn_query(context_, RKNN_QUERY_IN_OUT_NUM, &io_, sizeof(io_)), "query model I/O"); }
        catch (...) { rknn_destroy(context_); context_ = 0; throw; }
    }
    ~Network() { if (context_) rknn_destroy(context_); }
    Network(const Network&) = delete;
    Network& operator=(const Network&) = delete;

    std::vector<std::vector<float>> infer(const std::vector<const void*>& data, const std::vector<size_t>& bytes,
                                          const std::vector<rknn_tensor_type>& types, const std::vector<rknn_tensor_format>& formats) {
        if (data.size() != io_.n_input) throw std::runtime_error("unexpected model input count");
        std::vector<rknn_input> inputs(io_.n_input);
        for (size_t i = 0; i < inputs.size(); ++i) {
            inputs[i].index = i; inputs[i].buf = const_cast<void*>(data[i]); inputs[i].size = bytes[i];
            inputs[i].type = types[i]; inputs[i].fmt = formats[i]; inputs[i].pass_through = 0;
        }
        require(rknn_inputs_set(context_, static_cast<uint32_t>(inputs.size()), inputs.data()), "set model inputs");
        require(rknn_run(context_, nullptr), "run model");
        std::vector<rknn_output> outputs(io_.n_output);
        for (size_t i = 0; i < outputs.size(); ++i) { outputs[i].index = i; outputs[i].want_float = 1; }
        require(rknn_outputs_get(context_, static_cast<uint32_t>(outputs.size()), outputs.data(), nullptr), "get model outputs");
        std::vector<std::vector<float>> result;
        try {
            result.resize(outputs.size());
            for (size_t i = 0; i < outputs.size(); ++i) {
                rknn_tensor_attr attr{}; attr.index = i;
                require(rknn_query(context_, RKNN_QUERY_OUTPUT_ATTR, &attr, sizeof(attr)), "query output shape");
                result[i].assign(static_cast<float*>(outputs[i].buf), static_cast<float*>(outputs[i].buf) + attr.n_elems);
            }
            require(rknn_outputs_release(context_, static_cast<uint32_t>(outputs.size()), outputs.data()), "release model outputs");
        } catch (...) { rknn_outputs_release(context_, static_cast<uint32_t>(outputs.size()), outputs.data()); throw; }
        return result;
    }
private:
    rknn_context context_ = 0;
    rknn_input_output_num io_{};
};

struct Result { cv::Rect2d box; double confidence; bool initialized; };

std::vector<float> nchw_to_nhwc(const std::vector<float>& source, int channels, int height, int width) {
    if (source.size() != size_t(channels * height * width)) throw std::runtime_error("unexpected backbone feature shape");
    std::vector<float> target(source.size());
    for (int channel = 0; channel < channels; ++channel)
        for (int y = 0; y < height; ++y)
            for (int x = 0; x < width; ++x)
                target[(y * width + x) * channels + channel] = source[(channel * height + y) * width + x];
    return target;
}

class Tracker12 {
public:
    Tracker12(const std::string& root, const std::string& version, const std::string& precision, bool use_rga)
        : profile_(profile_for(version)), template_(file_for(root, version, precision, "nanotrack_backbone_template", false)),
          search_(file_for(root, version, precision, "nanotrack_backbone", false)),
          head_(file_for(root, version, precision, "nanotrack_head", true)), use_rga_(use_rga) {
        window_.resize(256);
        for (int y = 0, i = 0; y < 16; ++y) for (int x = 0; x < 16; ++x, ++i)
            window_[i] = (.5f - .5f * std::cos(2.f * float(CV_PI) * x / 15.f)) * (.5f - .5f * std::cos(2.f * float(CV_PI) * y / 15.f));
    }
    Result initialize(const cv::Mat& frame, const cv::Rect2d& roi, GstObject* owner) {
        center_ = {float(roi.x + (roi.width - 1) / 2), float(roi.y + (roi.height - 1) / 2)};
        size_ = {float(roi.width), float(roi.height)}; average_ = cv::mean(frame);
        const cv::Mat crop = make_crop(frame, std::lround(padded(size_.width, size_.height)), 127, owner);
        template_feature_ = nchw_to_nhwc(template_.infer({crop.data}, {crop.total() * crop.elemSize()}, {RKNN_TENSOR_UINT8}, {RKNN_TENSOR_NHWC}).at(0), 48, 8, 8);
        return {roi, 0, true};
    }
    Result track(const cv::Mat& frame, GstObject* owner) {
        const float template_size = padded(size_.width, size_.height), scale = 127.f / template_size;
        const cv::Mat crop = make_crop(frame, std::lround(template_size * 255.f / 127.f), 255, owner);
        const auto search_feature = nchw_to_nhwc(search_.infer({crop.data}, {crop.total() * crop.elemSize()}, {RKNN_TENSOR_UINT8}, {RKNN_TENSOR_NHWC}).at(0), 48, 16, 16);
        const auto outputs = head_.infer({template_feature_.data(), search_feature.data()},
            {template_feature_.size() * sizeof(float), search_feature.size() * sizeof(float)},
            {RKNN_TENSOR_FLOAT32, RKNN_TENSOR_FLOAT32}, {RKNN_TENSOR_NHWC, RKNN_TENSOR_NHWC});
        if (outputs.size() != 2 || outputs[0].size() != 512 || outputs[1].size() != 1024) throw std::runtime_error("unexpected V1/V2 head output shapes");
        float best_rank = -1, best_score = 0, best_penalty = 0; cv::Point2f offset; cv::Size2f proposal;
        for (int i = 0; i < 256; ++i) {
            const float bg = outputs[0][i], fg = outputs[0][256 + i], max_score = std::max(bg, fg);
            const float score = std::exp(fg - max_score) / (std::exp(bg - max_score) + std::exp(fg - max_score));
            const float px = float(i % 16 - 8) * 16.f, py = float(i / 16 - 8) * 16.f;
            const float left = px - outputs[1][i], top = py - outputs[1][256 + i];
            const float right = px + outputs[1][512 + i], bottom = py + outputs[1][768 + i];
            const float width = right - left, height = bottom - top;
            if (!std::isfinite(score) || !std::isfinite(width) || !std::isfinite(height) || width <= 0 || height <= 0) continue;
            const float shape = padded(width, height) / padded(size_.width * scale, size_.height * scale);
            const float ratio = (size_.width / size_.height) / (width / height);
            const float penalty = std::exp(-(std::max(shape, 1.f / shape) * std::max(ratio, 1.f / ratio) - 1) * profile_.penalty);
            const float rank = penalty * score * (1 - profile_.window) + window_[i] * profile_.window;
            if (rank > best_rank) { best_rank = rank; best_score = score; best_penalty = penalty; offset = {(left + right) / (2 * scale), (top + bottom) / (2 * scale)}; proposal = {width / scale, height / scale}; }
        }
        if (best_rank < 0) throw std::runtime_error("no valid V1/V2 tracking output");
        const float blend = best_penalty * best_score * profile_.learning;
        center_.x = std::clamp(center_.x + offset.x, 0.f, float(frame.cols)); center_.y = std::clamp(center_.y + offset.y, 0.f, float(frame.rows));
        size_.width = std::clamp(size_.width * (1 - blend) + proposal.width * blend, 10.f, float(frame.cols));
        size_.height = std::clamp(size_.height * (1 - blend) + proposal.height * blend, 10.f, float(frame.rows));
        return {{center_.x - size_.width / 2, center_.y - size_.height / 2, size_.width, size_.height}, best_score, false};
    }
private:
    cv::Mat make_crop(const cv::Mat& frame, int source_side, int destination_side, GstObject* owner) {
        if (source_side <= 0 || source_side > 65536) throw std::runtime_error("unsupported crop size");
        const int x = int(std::floor(center_.x - source_side * .5f)), y = int(std::floor(center_.y - source_side * .5f));
        cv::Mat source(source_side, source_side, CV_8UC3, average_);
        const cv::Rect valid = cv::Rect(x, y, source_side, source_side) & cv::Rect(0, 0, frame.cols, frame.rows);
        if (valid.empty()) throw std::runtime_error("crop is outside the frame");
        frame(valid).copyTo(source(cv::Rect(valid.x - x, valid.y - y, valid.width, valid.height)));
        cv::Mat result(destination_side, destination_side, CV_8UC3);
        if (use_rga_) {
            auto input = importbuffer_virtualaddr(source.data, int(source.total() * source.elemSize()));
            auto output = importbuffer_virtualaddr(result.data, int(result.total() * result.elemSize()));
            if (input && output && imresize(wrapbuffer_handle(input, source_side, source_side, RK_FORMAT_BGR_888), wrapbuffer_handle(output, destination_side, destination_side, RK_FORMAT_BGR_888)) == IM_STATUS_SUCCESS) {
                releasebuffer_handle(input); releasebuffer_handle(output); return result;
            }
            if (input) releasebuffer_handle(input);
            if (output) releasebuffer_handle(output);
            GST_WARNING_OBJECT(owner, "RGA resize failed; using OpenCV for this and subsequent frames"); use_rga_ = false;
        }
        cv::resize(source, result, result.size(), 0, 0, cv::INTER_LINEAR); return result;
    }
    Profile profile_; Network template_, search_, head_; bool use_rga_; cv::Point2f center_; cv::Size2f size_; cv::Scalar average_; std::vector<float> template_feature_, window_;
};

struct State { std::mutex mutex; std::string roi, models_dir, version = "v2", precision = "mixed", resize = "auto"; bool enabled = false, started = false, reset = true; GstVideoInfo info{}; std::unique_ptr<Tracker12> tracker; };
} // namespace

typedef struct _GstRknnNanoTracker12 { GstBaseTransform parent; State* state; } GstRknnNanoTracker12;
typedef struct _GstRknnNanoTracker12Class { GstBaseTransformClass parent_class; } GstRknnNanoTracker12Class;
G_DEFINE_TYPE(GstRknnNanoTracker12, gst_rknn_nano_tracker12, GST_TYPE_BASE_TRANSFORM)
enum { PROP_0, PROP_ENABLED, PROP_ROI, PROP_MODELS_DIR, PROP_MODEL_VERSION, PROP_PRECISION, PROP_RESIZE };
static GstStaticPadTemplate sink_template = GST_STATIC_PAD_TEMPLATE("sink", GST_PAD_SINK, GST_PAD_ALWAYS, GST_STATIC_CAPS("video/x-raw,format=BGR,width=[10,16384],height=[10,16384],interlace-mode=progressive"));
static GstStaticPadTemplate src_template = GST_STATIC_PAD_TEMPLATE("src", GST_PAD_SRC, GST_PAD_ALWAYS, GST_STATIC_CAPS("video/x-raw,format=BGR,width=[10,16384],height=[10,16384],interlace-mode=progressive"));

static void set_property(GObject* object, guint property, const GValue* value, GParamSpec* spec) {
    auto* self = reinterpret_cast<GstRknnNanoTracker12*>(object); auto& state = *self->state;
    std::lock_guard<std::mutex> lock(state.mutex);
    if (property >= PROP_MODELS_DIR && state.started) { GST_WARNING_OBJECT(self, "%s can only change in NULL or READY", spec->name); return; }
    const std::string string = G_VALUE_HOLDS_STRING(value) ? g_value_get_string(value) : "";
    switch (property) {
    case PROP_ENABLED: if (state.enabled != bool(g_value_get_boolean(value))) state.reset = true; state.enabled = g_value_get_boolean(value); break;
    case PROP_ROI: state.roi = string; state.reset = true; break;
    case PROP_MODELS_DIR: state.models_dir = string; break;
    case PROP_MODEL_VERSION: state.version = string; break;
    case PROP_PRECISION: state.precision = string; break;
    case PROP_RESIZE: state.resize = string; break;
    default: G_OBJECT_WARN_INVALID_PROPERTY_ID(object, property, spec);
    }
}
static void get_property(GObject* object, guint property, GValue* value, GParamSpec* spec) {
    auto& state = *reinterpret_cast<GstRknnNanoTracker12*>(object)->state; std::lock_guard<std::mutex> lock(state.mutex);
    switch (property) {
    case PROP_ENABLED: g_value_set_boolean(value, state.enabled); break;
    case PROP_ROI: g_value_set_string(value, state.roi.c_str()); break;
    case PROP_MODELS_DIR: g_value_set_string(value, state.models_dir.c_str()); break;
    case PROP_MODEL_VERSION: g_value_set_string(value, state.version.c_str()); break;
    case PROP_PRECISION: g_value_set_string(value, state.precision.c_str()); break;
    case PROP_RESIZE: g_value_set_string(value, state.resize.c_str()); break;
    default: G_OBJECT_WARN_INVALID_PROPERTY_ID(object, property, spec);
    }
}
static gboolean start(GstBaseTransform* base) {
    auto& state = *reinterpret_cast<GstRknnNanoTracker12*>(base)->state; std::lock_guard<std::mutex> lock(state.mutex);
    if ((state.version != "v1" && state.version != "v2") || (state.precision != "fp16" && state.precision != "mixed" && state.precision != "int8" && state.precision != "int8-mmse") || (state.resize != "auto" && state.resize != "cpu")) {
        GST_ELEMENT_ERROR(base, RESOURCE, SETTINGS, ("Invalid V1/V2 tracker setting"), (nullptr)); return FALSE;
    }
    state.started = true; state.reset = true; return TRUE;
}
static gboolean stop(GstBaseTransform* base) {
    auto& state = *reinterpret_cast<GstRknnNanoTracker12*>(base)->state; std::lock_guard<std::mutex> lock(state.mutex);
    state.tracker.reset(); state.reset = true; state.started = false; return TRUE;
}
static gboolean set_caps(GstBaseTransform* base, GstCaps* caps, GstCaps*) {
    auto& state = *reinterpret_cast<GstRknnNanoTracker12*>(base)->state; GstVideoInfo info;
    if (!gst_video_info_from_caps(&info, caps) || GST_VIDEO_INFO_FORMAT(&info) != GST_VIDEO_FORMAT_BGR || GST_VIDEO_INFO_IS_INTERLACED(&info)) return FALSE;
    std::lock_guard<std::mutex> lock(state.mutex);
    if (GST_VIDEO_INFO_WIDTH(&state.info) != GST_VIDEO_INFO_WIDTH(&info) || GST_VIDEO_INFO_HEIGHT(&state.info) != GST_VIDEO_INFO_HEIGHT(&info)) state.reset = true;
    state.info = info; return TRUE;
}
static gboolean sink_event(GstBaseTransform* base, GstEvent* event) {
    if (GST_EVENT_TYPE(event) == GST_EVENT_STREAM_START || GST_EVENT_TYPE(event) == GST_EVENT_SEGMENT || GST_EVENT_TYPE(event) == GST_EVENT_FLUSH_STOP) {
        auto& state = *reinterpret_cast<GstRknnNanoTracker12*>(base)->state; std::lock_guard<std::mutex> lock(state.mutex); state.reset = true;
    }
    return GST_BASE_TRANSFORM_CLASS(gst_rknn_nano_tracker12_parent_class)->sink_event(base, event);
}
static GstFlowReturn transform_ip(GstBaseTransform* base, GstBuffer* buffer) {
    auto& state = *reinterpret_cast<GstRknnNanoTracker12*>(base)->state; GstVideoFrame frame{}; bool mapped = false;
    try {
        std::lock_guard<std::mutex> lock(state.mutex);
        if (GST_BUFFER_FLAG_IS_SET(buffer, GST_BUFFER_FLAG_DISCONT)) state.reset = true;
        if (!state.enabled) return GST_FLOW_OK;
        if (!gst_video_frame_map(&frame, &state.info, buffer, GST_MAP_READ)) throw std::runtime_error("cannot map BGR frame");
        mapped = true;
        const int width = GST_VIDEO_FRAME_WIDTH(&frame), height = GST_VIDEO_FRAME_HEIGHT(&frame), stride = GST_VIDEO_FRAME_PLANE_STRIDE(&frame, 0);
        if (stride < width * 3) throw std::runtime_error("invalid BGR stride");
        cv::Mat image(height, width, CV_8UC3, GST_VIDEO_FRAME_PLANE_DATA(&frame, 0), stride);
        if (!state.tracker) state.tracker = std::make_unique<Tracker12>(state.models_dir, state.version, state.precision, state.resize == "auto");
        const Result result = state.reset ? state.tracker->initialize(image, roi_from_text(state.roi, width, height), GST_OBJECT(base)) : state.tracker->track(image, GST_OBJECT(base));
        state.reset = false; gst_video_frame_unmap(&frame); mapped = false;
        const int x = std::clamp(int(std::floor(result.box.x)), 0, width), y = std::clamp(int(std::floor(result.box.y)), 0, height);
        const int right = std::clamp(int(std::ceil(result.box.x + result.box.width)), 0, width), bottom = std::clamp(int(std::ceil(result.box.y + result.box.height)), 0, height);
        auto* meta = gst_buffer_add_video_region_of_interest_meta(buffer, "nanotrack", x, y, right - x, bottom - y);
        if (!meta) throw std::runtime_error("cannot attach ROI metadata");
        auto* parameters = gst_structure_new("nanotrack", "initialized", G_TYPE_BOOLEAN, result.initialized, nullptr);
        if (!result.initialized) gst_structure_set(parameters, "confidence", G_TYPE_DOUBLE, result.confidence, nullptr);
        gst_video_region_of_interest_meta_add_param(meta, parameters);
        return GST_FLOW_OK;
    } catch (const std::exception& error) {
        if (mapped) gst_video_frame_unmap(&frame);
        GST_ELEMENT_ERROR(base, STREAM, FAILED, ("NanoTracker V1/V2 frame processing failed"), ("%s", error.what())); return GST_FLOW_ERROR;
    }
}
static void finalize(GObject* object) { delete reinterpret_cast<GstRknnNanoTracker12*>(object)->state; G_OBJECT_CLASS(gst_rknn_nano_tracker12_parent_class)->finalize(object); }
static void gst_rknn_nano_tracker12_class_init(GstRknnNanoTracker12Class* klass) {
    auto* object = G_OBJECT_CLASS(klass); auto* element = GST_ELEMENT_CLASS(klass); auto* transform = GST_BASE_TRANSFORM_CLASS(klass);
    object->set_property = set_property; object->get_property = get_property; object->finalize = finalize;
    const auto live = GParamFlags(G_PARAM_READWRITE | G_PARAM_STATIC_STRINGS | GST_PARAM_MUTABLE_PLAYING), ready = GParamFlags(G_PARAM_READWRITE | G_PARAM_STATIC_STRINGS | GST_PARAM_MUTABLE_READY);
    g_object_class_install_property(object, PROP_ENABLED, g_param_spec_boolean("enabled", "Enabled", "Track the configured ROI; enabling captures a fresh template", false, live));
    g_object_class_install_property(object, PROP_ROI, g_param_spec_string("roi", "ROI", "Initial x,y,width,height; assignment resets tracking", "", live));
    g_object_class_install_property(object, PROP_MODELS_DIR, g_param_spec_string("models-dir", "Models directory", "Root containing V1 and V2 model directories", "", ready));
    g_object_class_install_property(object, PROP_MODEL_VERSION, g_param_spec_string("model-version", "Model version", "V1 or V2 model set", "v2", ready));
    g_object_class_install_property(object, PROP_PRECISION, g_param_spec_string("precision", "Precision", "Model filename set: fp16, mixed, int8, int8-mmse", "mixed", ready));
    g_object_class_install_property(object, PROP_RESIZE, g_param_spec_string("resize", "Resize", "auto: RGA then OpenCV fallback; cpu: OpenCV", "auto", ready));
    gst_element_class_set_static_metadata(element, "RKNN NanoTracker V1/V2", "Filter/Metadata/Video", "Tracks one ROI with independent NanoTrack V1/V2 RKNN models", "gst-rknn");
    gst_element_class_add_static_pad_template(element, &sink_template); gst_element_class_add_static_pad_template(element, &src_template);
    transform->start = GST_DEBUG_FUNCPTR(start); transform->stop = GST_DEBUG_FUNCPTR(stop); transform->set_caps = GST_DEBUG_FUNCPTR(set_caps); transform->sink_event = GST_DEBUG_FUNCPTR(sink_event); transform->transform_ip = GST_DEBUG_FUNCPTR(transform_ip);
}
static void gst_rknn_nano_tracker12_init(GstRknnNanoTracker12* self) { self->state = new State; gst_video_info_init(&self->state->info); gst_base_transform_set_in_place(GST_BASE_TRANSFORM(self), TRUE); }
static gboolean plugin_init(GstPlugin* plugin) { GST_DEBUG_CATEGORY_INIT(nanotracker12_debug, "rknnnanotracker12", 0, "RKNN NanoTracker V1/V2"); return gst_element_register(plugin, "rknnnanotracker12", GST_RANK_NONE, gst_rknn_nano_tracker12_get_type()); }
GST_PLUGIN_DEFINE(GST_VERSION_MAJOR, GST_VERSION_MINOR, rknnnanotracker12, "NanoTracker V1/V2 RKNN tracking metadata", plugin_init, "1.0", "LGPL", "gst-rknn", "https://example.com")
