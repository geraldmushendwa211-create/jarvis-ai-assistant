from skills.video_editor import add_background_music

result = add_background_music("workspace/output/output_with_captions.mp4")

if result:
    print(f"Success! Saved to: {result}")
else:
    print("Something went wrong — check the error above.")