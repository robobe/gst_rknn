# NanoTracker synthetic motion fixture

`generate_move_right.py` creates `assets/nanotracker/move_right_500.mp4`, a
640×360, 30-FPS, 500-frame video. A fixed, textured 64×64 target moves from
left to right; the matching ground truth is recorded as
`frame,pts_ns,x,y,width,height`.

```sh
./generate_move_right.py
```

The first-frame ROI is `20,148,64,64`. The fixture validates pipeline and
metadata mechanics. It does not replace annotated real video for accuracy
validation because NanoTrackV3 was trained on natural visual targets.

Deploy with `./scripts/deploy.sh assets`, then run it on the board with:

```sh
./scripts/nanotracker/test.sh video
./scripts/nanotracker/test.sh compare
```
