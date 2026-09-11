#include <gst/base/gstbasetransform.h>
#include <gst/gst.h>

#include <iostream>

#ifndef PACKAGE
#define PACKAGE "gst-rknn"
#endif

typedef struct _GstRknnHello { GstBaseTransform parent; } GstRknnHello;
typedef struct _GstRknnHelloClass { GstBaseTransformClass parent_class; } GstRknnHelloClass;

G_DEFINE_TYPE(GstRknnHello, gst_rknn_hello, GST_TYPE_BASE_TRANSFORM)

static GstStaticPadTemplate sink_template = GST_STATIC_PAD_TEMPLATE(
    "sink", GST_PAD_SINK, GST_PAD_ALWAYS, GST_STATIC_CAPS("video/x-raw"));
static GstStaticPadTemplate src_template = GST_STATIC_PAD_TEMPLATE(
    "src", GST_PAD_SRC, GST_PAD_ALWAYS, GST_STATIC_CAPS("video/x-raw"));

static gboolean gst_rknn_hello_start(GstBaseTransform *) {
  std::cout << "Hello Radxa" << std::endl;
  return TRUE;
}

static GstFlowReturn gst_rknn_hello_transform_ip(GstBaseTransform *, GstBuffer *) {
  return GST_FLOW_OK;
}

static void gst_rknn_hello_class_init(GstRknnHelloClass *klass) {
  auto *element_class = GST_ELEMENT_CLASS(klass);
  auto *transform_class = GST_BASE_TRANSFORM_CLASS(klass);
  gst_element_class_set_static_metadata(element_class, "RKNN hello filter",
                                        "Filter/Video", "Radxa bring-up filter", "gst-rknn");
  gst_element_class_add_static_pad_template(element_class, &sink_template);
  gst_element_class_add_static_pad_template(element_class, &src_template);
  transform_class->start = gst_rknn_hello_start;
  transform_class->transform_ip = gst_rknn_hello_transform_ip;
}

static void gst_rknn_hello_init(GstRknnHello *self) {
  gst_base_transform_set_in_place(GST_BASE_TRANSFORM(self), TRUE);
}

static gboolean plugin_init(GstPlugin *plugin) {
  return gst_element_register(plugin, "rknnhello", GST_RANK_NONE, gst_rknn_hello_get_type());
}

GST_PLUGIN_DEFINE(GST_VERSION_MAJOR, GST_VERSION_MINOR, rknnhello,
                  "Radxa RKNN hello plugin", plugin_init, "0.1.0", "LGPL",
                  "gst-rknn", "https://example.invalid/gst-rknn")
