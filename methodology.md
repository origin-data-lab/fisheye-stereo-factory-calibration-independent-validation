# Methodology
* Kalibr equidistant intrinsics at 800×600 converted to 1600×1200: f×2, c×2+0.5.
* Reprojection: undistort detected corners, PnP (iterative) for pose with intrinsics fixed, fisheye projectPoints, Euclidean residual.
* Epipolar: E = [t]× R from cam1←cam0; distance of the normalised right point to the epipolar line, ×fx to pixels.
* Grid: 200 px cells, cells with <30 points left blank. Radius bands from the principal point.
* Recalibration: cv2.fisheye.calibrate per camera (initialised from factory), stereo extrinsics with intrinsics fixed on undistorted normalised points; outlier views >3× median per-view error removed once; split-half by alternating views.
