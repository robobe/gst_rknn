gst-launch-1.0   \
  udpsrc port=5004 caps='application/x-rtp,media=video,encoding-name=H264,payload=96,clock-rate=90000' \
  ! rtpjitterbuffer latency=50 drop-on-latency=true \
  ! rtph264depay \
  ! h264parse \
  ! avdec_h264 \
  ! videoconvert \
  ! fpsdisplaysink  sync=false