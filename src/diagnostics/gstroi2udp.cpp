#include <gst/base/gstbasetransform.h>
#include <gst/video/video.h>

#include <arpa/inet.h>
#include <netdb.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <cstring>
#include <sstream>
#include <string>

#ifndef PACKAGE
#define PACKAGE "gst-rknn"
#endif

struct State {
  std::string host;
  guint port = 5005;
  int socket = -1;
  sockaddr_storage destination{};
  socklen_t destination_length = 0;
};

typedef struct _GstRoi2Udp { GstBaseTransform parent; State *state; } GstRoi2Udp;
typedef struct _GstRoi2UdpClass { GstBaseTransformClass parent_class; } GstRoi2UdpClass;
G_DEFINE_TYPE(GstRoi2Udp, gst_roi2udp, GST_TYPE_BASE_TRANSFORM)

enum { PROP_0, PROP_HOST, PROP_PORT };
static GstStaticPadTemplate sink_template = GST_STATIC_PAD_TEMPLATE(
    "sink", GST_PAD_SINK, GST_PAD_ALWAYS, GST_STATIC_CAPS("video/x-raw"));
static GstStaticPadTemplate src_template = GST_STATIC_PAD_TEMPLATE(
    "src", GST_PAD_SRC, GST_PAD_ALWAYS, GST_STATIC_CAPS("video/x-raw"));

static bool open_udp(State *state) {
  addrinfo hints{};
  hints.ai_family = AF_UNSPEC;
  hints.ai_socktype = SOCK_DGRAM;
  addrinfo *results = nullptr;
  const std::string service = std::to_string(state->port);
  if (getaddrinfo(state->host.c_str(), service.c_str(), &hints, &results) != 0) return false;
  for (auto *item = results; item; item = item->ai_next) {
    const int socket_fd = socket(item->ai_family, item->ai_socktype, item->ai_protocol);
    if (socket_fd < 0) continue;
    state->socket = socket_fd;
    std::memcpy(&state->destination, item->ai_addr, item->ai_addrlen);
    state->destination_length = item->ai_addrlen;
    break;
  }
  freeaddrinfo(results);
  return state->socket >= 0;
}

static bool send_packet(const State *state, const std::string &line) {
  return sendto(state->socket, line.data(), line.size(), MSG_NOSIGNAL,
                reinterpret_cast<const sockaddr *>(&state->destination), state->destination_length) ==
         static_cast<ssize_t>(line.size());
}

static void set_property(GObject *object, guint id, const GValue *value, GParamSpec *spec) {
  auto *self = reinterpret_cast<GstRoi2Udp *>(object);
  switch (id) {
    case PROP_HOST: {
      const char *host = g_value_get_string(value);
      self->state->host = host ? host : "";
      break;
    }
    case PROP_PORT: self->state->port = g_value_get_uint(value); break;
    default: G_OBJECT_WARN_INVALID_PROPERTY_ID(object, id, spec);
  }
}

static void get_property(GObject *object, guint id, GValue *value, GParamSpec *spec) {
  auto *self = reinterpret_cast<GstRoi2Udp *>(object);
  switch (id) {
    case PROP_HOST: g_value_set_string(value, self->state->host.c_str()); break;
    case PROP_PORT: g_value_set_uint(value, self->state->port); break;
    default: G_OBJECT_WARN_INVALID_PROPERTY_ID(object, id, spec);
  }
}

static gboolean start(GstBaseTransform *base) {
  auto *self = reinterpret_cast<GstRoi2Udp *>(base);
  if (self->state->host.empty()) {
    GST_ELEMENT_ERROR(self, RESOURCE, SETTINGS, ("host is required"), (nullptr));
    return FALSE;
  }
  if (!open_udp(self->state)) {
    GST_ELEMENT_ERROR(self, RESOURCE, OPEN_WRITE, ("Cannot create metadata UDP socket"),
                      ("%s:%u: %s", self->state->host.c_str(), self->state->port, g_strerror(errno)));
    return FALSE;
  }
  return TRUE;
}

static gboolean stop(GstBaseTransform *base) {
  auto *self = reinterpret_cast<GstRoi2Udp *>(base);
  if (self->state->socket >= 0) close(self->state->socket);
  self->state->socket = -1;
  return TRUE;
}

static GstFlowReturn transform_ip(GstBaseTransform *base, GstBuffer *buffer) {
  auto *self = reinterpret_cast<GstRoi2Udp *>(base);
  gpointer cursor = nullptr;
  while (auto *raw = gst_buffer_iterate_meta_filtered(
             buffer, &cursor, GST_VIDEO_REGION_OF_INTEREST_META_API_TYPE)) {
    auto *roi = reinterpret_cast<GstVideoRegionOfInterestMeta *>(raw);
    const char *type = g_quark_to_string(roi->roi_type);
    auto *parameters = type ? gst_video_region_of_interest_meta_get_param(roi, type) : nullptr;
    gboolean initialized = FALSE;
    gdouble confidence = 0;
    const bool has_confidence = parameters && gst_structure_get_double(parameters, "confidence", &confidence);
    if (parameters) gst_structure_get_boolean(parameters, "initialized", &initialized);
    std::ostringstream line;
    line << GST_BUFFER_PTS(buffer) << ',' << (type ? type : "") << ',' << roi->x << ','
         << roi->y << ',' << roi->w << ',' << roi->h << ',' << (initialized ? 1 : 0) << ',';
    if (has_confidence) line << confidence;
    line << '\n';
    (void)send_packet(self->state, line.str());
  }
  return GST_FLOW_OK;
}

static void finalize(GObject *object) {
  delete reinterpret_cast<GstRoi2Udp *>(object)->state;
  G_OBJECT_CLASS(gst_roi2udp_parent_class)->finalize(object);
}

static void gst_roi2udp_class_init(GstRoi2UdpClass *klass) {
  auto *object = G_OBJECT_CLASS(klass);
  auto *element = GST_ELEMENT_CLASS(klass);
  auto *transform = GST_BASE_TRANSFORM_CLASS(klass);
  object->set_property = set_property;
  object->get_property = get_property;
  object->finalize = finalize;
  const auto ready = GParamFlags(G_PARAM_READWRITE | G_PARAM_STATIC_STRINGS | GST_PARAM_MUTABLE_READY);
  g_object_class_install_property(object, PROP_HOST, g_param_spec_string("host", "Host", "Metadata UDP host", "", ready));
  g_object_class_install_property(object, PROP_PORT, g_param_spec_uint("port", "Port", "Metadata UDP port", 1, 65535, 5005, ready));
  gst_element_class_set_static_metadata(element, "ROI metadata UDP sender", "Filter/Diagnostics/Video",
                                        "Sends one GstVideoRegionOfInterestMeta CSV record per UDP datagram", "gst-rknn");
  gst_element_class_add_static_pad_template(element, &sink_template);
  gst_element_class_add_static_pad_template(element, &src_template);
  transform->start = start;
  transform->stop = stop;
  transform->transform_ip = transform_ip;
}

static void gst_roi2udp_init(GstRoi2Udp *self) {
  self->state = new State;
  gst_base_transform_set_in_place(GST_BASE_TRANSFORM(self), TRUE);
}

static gboolean plugin_init(GstPlugin *plugin) {
  return gst_element_register(plugin, "roi2udp", GST_RANK_NONE, gst_roi2udp_get_type());
}

GST_PLUGIN_DEFINE(GST_VERSION_MAJOR, GST_VERSION_MINOR, roi2udp,
                  "ROI metadata UDP sender", plugin_init, "0.1.0", "LGPL",
                  "gst-rknn", "https://example.invalid/gst-rknn")
