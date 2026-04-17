import os

from gradio_app import launch_app


if __name__ == "__main__":
    launch_app(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", "7860")),
        debug=False,
    )
