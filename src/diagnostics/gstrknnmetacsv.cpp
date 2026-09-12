#include <gst/base/gstbasetransform.h>
#include <gst/video/video.h>

#include <fstream>
#include <memory>
#include <string>

#ifndef PACKAGE
#define PACKAGE "gst-rknn"
#endif

struct State {
  std::string location;
  std::ofstream output;
};

typedef struct _GstRknnMetaCsv {
  GstBaseTransform parent;
  State *state;
} GstRknnMetaCsv;

typedef struct _GstRknnMetaCsvClass {
  GstBaseTransformClass parent_class;
} GstRknnMetaCsvClass;

G_DEFINE_TYPE(GstRknnMetaCsv, gst_rknn_meta_csv, GST_TYPE_BASE_TRANSFORM)

enum { PROP_0, PROP_LOCATION };

static GstStaticPadTemplate sink_template = GST_STATIC_PAD_TEMPLATE(
    "sink", GST_PAD_SINK, GST_PAD_ALWAYS, GST_STATIC_CAPS("video/x-raw"));
static GstStaticPadTemplate src_template = GST_STATIC_PAD_TEMPLATE(
    "src", GST_PAD_SRC, GST_PAD_ALWAYS, GST_STATIC_CAPS("video/x-raw"));

static void set_property(GObject *object, guint id, const GValue *value, GParamSpec *spec) {
  auto *self = reinterpret_cast<GstRknnMetaCsv *>(object);
  if (id == PROP_LOCATION) {
    const char *location = g_value_get_string(value);
    self->state->location = location ? location : "";
  } else {
    G_OBJECT_WARN_INVALID_PROPERTY_ID(object, id, spec);
  }
}

static void get_property(GObject *object, guint id, GValue *value, GParamSpec *spec) {
  auto *self = reinterpret_cast<GstRknnMetaCsv *>(object);
  if (id == PROP_LOCATION) {
    g_value_set_string(value, self->state->location.c_str());
  } else {
    G_OBJECT_WARN_INVALID_PROPERTY_ID(object, id, spec);
  }
}

static gboolean start(GstBaseTransform *base) {
  auto *self = reinterpret_cast<GstRknnMetaCsv *>(base);
  if (self->state->location.empty()) {
    GST_ELEMENT_ERROR(self, RESOURCE, SETTINGS, ("location is required"), (nullptr));
    return FALSE;
  }
  self->state->output.open(self->state->location, std::ios::trunc);
  if (!self->state->output) {
    GST_ELEMENT_ERROR(self, RESOURCE, OPEN_WRITE, ("Cannot open CSV output"),
                      ("%s", self->state->location.c_str()));
    return FALSE;
  }
  self->state->output << "pts_ns,roi_type,x,y,width,height,initialized,confidence,class_id\n";
  return TRUE;
}

static gboolean stop(GstBaseTransform *base) {
  auto *self = reinterpret_cast<GstRknnMetaCsv *>(base);
  if (self->state->output.is_open()) self->state->output.close();
  return TRUE;
}

static GstFlowReturn transform_ip(GstBaseTransform *base, GstBuffer *buffer) {
  auto *self = reinterpret_cast<GstRknnMetaCsv *>(base);
  gpointer cursor = nullptr;
  while (auto *raw = gst_buffer_iterate_meta_filtered(
             buffer, &cursor, GST_VIDEO_REGION_OF_INTEREST_META_API_TYPE)) {
    auto *roi = reinterpret_cast<GstVideoRegionOfInterestMeta *>(raw);
    const char *type = g_quark_to_string(roi->roi_type);
    auto *parameters = type ? gst_video_region_of_interest_meta_get_param(roi, type) : nullptr;
    gboolean initialized = FALSE;
    gdouble confidence = 0;
    const bool has_confidence = parameters &&
        gst_structure_get_double(parameters, "confidence", &confidence);
    if (parameters) gst_structure_get_boolean(parameters, "initialized", &initialized);

    self->state->output << GST_BUFFER_PTS(buffer) << ',' << (type ? type : "") << ','
                        << roi->x << ',' << roi->y << ','
                        << roi->w << ',' << roi->h << ',' << (initialized ? 1 : 0) << ',';
    if (has_confidence) self->state->output << confidence;
    self->state->output << ',';
    if (type && std::string(type) == "yolo8") self->state->output << roi->id;
    self->state->output << '\n';
    if (!self->state->output) {
      GST_ELEMENT_ERROR(self, RESOURCE, WRITE, ("Cannot write CSV output"), (nullptr));
      return GST_FLOW_ERROR;
    }
  }
  return GST_FLOW_OK;
}

static void finalize(GObject *object) {
  delete reinterpret_cast<GstRknnMetaCsv *>(object)->state;
  G_OBJECT_CLASS(gst_rknn_meta_csv_parent_class)->finalize(object);
}

static void gst_rknn_meta_csv_class_init(GstRknnMetaCsvClass *klass) {
  auto *object = G_OBJECT_CLASS(klass);
  auto *element = GST_ELEMENT_CLASS(klass);
  auto *transform = GST_BASE_TRANSFORM_CLASS(klass);
  object->set_property = set_property;
  object->get_property = get_property;
  object->finalize = finalize;
  g_object_class_install_property(
      object, PROP_LOCATION,
      g_param_spec_string("location", "Location", "CSV output file", "",
                          GParamFlags(G_PARAM_READWRITE | G_PARAM_STATIC_STRINGS | GST_PARAM_MUTABLE_READY)));
  gst_element_class_set_static_metadata(element, "ROI metadata CSV writer", "Filter/Diagnostics/Video",
                                        "Writes GstVideoRegionOfInterestMeta to CSV", "gst-rknn");
  gst_element_class_add_static_pad_template(element, &sink_template);
  gst_element_class_add_static_pad_template(element, &src_template);
  transform->start = start;
  transform->stop = stop;
  transform->transform_ip = transform_ip;
}

static void gst_rknn_meta_csv_init(GstRknnMetaCsv *self) {
  self->state = new State;
  gst_base_transform_set_in_place(GST_BASE_TRANSFORM(self), TRUE);
}

static gboolean plugin_init(GstPlugin *plugin) {
  return gst_element_register(plugin, "roi2csv", GST_RANK_NONE, gst_rknn_meta_csv_get_type());
}

GST_PLUGIN_DEFINE(GST_VERSION_MAJOR, GST_VERSION_MINOR, roi2csv,
                  "ROI metadata CSV writer", plugin_init, "0.1.0", "LGPL",
                  "gst-rknn", "https://example.invalid/gst-rknn")
