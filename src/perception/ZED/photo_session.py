from src.perception.ZED.cameralib import Camera
with Camera() as camera:


    #camera.shoot_many(OUTPUT_DIR)

    camera.capture_and_crop(
        output_path="zed_platform_test",
        x=1460,
        y=220,
        width=150,
        height=150,
    )
