gst-launch-1.0   \
  udpsrc port=5004 caps='application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000' \
  ! rtpjitterbuffer latency=200 drop-on-latency=false \
  ! rtph264depay \
  ! h264parse \
  ! avdec_h264 \
  ! videoconvert \
  ! fpsdisplaysink  sync=false
