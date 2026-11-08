import os
import replicate
from dotenv import load_dotenv

# Load environment variables from .env file if you're using one
load_dotenv()


# The Replicate token must come from the environment or .env, never from source.
if not os.environ.get('REPLICATE_API_TOKEN'):
    raise SystemExit('Set REPLICATE_API_TOKEN in your environment or .env file.')

deployment = replicate.deployments.get("codejedi-ai/sdxl-mekkana")
prediction = deployment.predictions.create(
    input={
        "disable_safety_checker": True,
        "image": "https://replicate.delivery/yhqm/V2bjVajXYeyGIi5K5rZCfxZNMWzfqqz8cVSmu30uHy0DDrTnA/out-0.png",
        "width": 1024,
        "height": 1024,
        "prompt": "regenerate the image in the same style however replace the person with Mekkana with blue hair",
        "refine": "no_refiner",
        "scheduler": "K_EULER",
        "lora_scale": 0.6,
        "num_outputs": 1,
        "guidance_scale": 7.5,
        "apply_watermark": True,
        "high_noise_frac": 0.8,
        "negative_prompt": "back facing\nhair in eyes\ndeformed face\nthree legs\nBlack Shirt\nWhite Pants",
        "prompt_strength": 0.8,
        "num_inference_steps": 50
    }
)
prediction.wait()
print(prediction.output)
# download the output image
def inpyt_2():
    celebs_list = ["Beyonce", "Taylor Swift", "Jennifer Lawrence", "Katy Perry", "Rihanna"]
    celebs_list = ["Victoria De Angelis"]
    imgurl = 'https://replicate.delivery/pbxt/p6sJwErbnLZ3AJizaVrFDMmfs3OgS6dnrFcQc00i9apQGM0JA/out-0.png'
    height = 1024
    width = height
    input={
            "image": imgurl,
            "disable_safety_checker": True,
            "width": width,
            "height": height,
            "prompt": f"Mekkana with blue hair wearing a long sleeved white compression shirt with (white embossing pattern) \n Generate in the theme of the music video I want to be your slave {celebs_list}",
            "refine": "base_image_refiner",
            "scheduler": "K_EULER",
            "lora_scale": 0.8,
            "num_outputs": 1,
            "guidance_scale": 7.5,
            "apply_watermark": True,
            "high_noise_frac": 0.8,
            "negative_prompt": "dark_skin\nback facing\nhair in eyes\ndeformed face\nthree legs\nBlack Shirt\nWhite Pants\ndeformed hands",
            "prompt_strength": 0.6,
            "num_inference_steps": 50
        }
    return input
