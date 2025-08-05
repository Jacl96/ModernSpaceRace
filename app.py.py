from flask import Flask, request, jsonify
import os
import requests
from io import BytesIO
import tweepy
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)

### TWITTER SETUP ###
auth = tweepy.OAuth1UserHandler(
    os.getenv("TWITTER_API_KEY"),
    os.getenv("TWITTER_API_SECRET"),
    os.getenv("TWITTER_ACCESS_TOKEN"),
    os.getenv("TWITTER_ACCESS_SECRET")
)
twitter_api = tweepy.API(auth)

### ENV VARS ###
FB_PAGE_ID = os.getenv("FB_PAGE_ID")
FB_TOKEN = os.getenv("FB_PAGE_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
LINKEDIN_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN")
LINKEDIN_ORG = os.getenv("LINKEDIN_ORGANIZATION_ID")
ZAPIER_PINTEREST_WEBHOOK_URL = os.getenv("ZAPIER_PINTEREST_WEBHOOK_URL")

### HELPERS ###
def post_to_twitter(text, image_url):
    try:
        img_data = requests.get(image_url).content
        img_file = BytesIO(img_data)
        media = twitter_api.media_upload(filename="cover.jpg", file=img_file)
        twitter_api.update_status(status=text, media_ids=[media.media_id])
        print("✅ Twitter posted")
    except Exception as e:
        print("❌ Twitter error:", e)

def post_to_facebook(text, image_url):
    try:
        fb_url = f"https://graph.facebook.com/{FB_PAGE_ID}/photos"
        payload = {
            'url': image_url,
            'caption': text,
            'access_token': FB_TOKEN
        }
        r = requests.post(fb_url, data=payload)
        print("✅ Facebook posted:", r.json())
    except Exception as e:
        print("❌ Facebook error:", e)

def post_to_instagram(text, image_url):
    try:
        # Step 1: Create container
        create_url = f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media"
        create_payload = {
            'image_url': image_url,
            'caption': text,
            'access_token': FB_TOKEN
        }
        create_res = requests.post(create_url, data=create_payload).json()
        creation_id = create_res.get('id')

        if not creation_id:
            raise Exception("No IG container ID returned")

        # Step 2: Publish media
        publish_url = f"https://graph.facebook.com/v18.0/{IG_USER_ID}/media_publish"
        publish_res = requests.post(publish_url, data={
            'creation_id': creation_id,
            'access_token': FB_TOKEN
        }).json()
        print("✅ Instagram posted:", publish_res)
    except Exception as e:
        print("❌ Instagram error:", e)

def post_to_linkedin(text, image_url):
    try:
        api_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
        headers = {
            "Authorization": f"Bearer {LINKEDIN_TOKEN}",
            "Content-Type": "application/json"
        }

        register_payload = {
            "registerUploadRequest": {
                "owner": f"urn:li:organization:{LINKEDIN_ORG}",
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "serviceRelationships": [{
                    "identifier": "urn:li:userGeneratedContent",
                    "relationshipType": "OWNER"
                }]
            }
        }

        upload_init = requests.post(api_url, headers=headers, json=register_payload).json()
        upload_url = upload_init['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
        asset_urn = upload_init['value']['asset']

        # Upload image binary
        img_bytes = requests.get(image_url).content
        requests.put(upload_url, data=img_bytes, headers={"Authorization": f"Bearer {LINKEDIN_TOKEN}"})

        # Share the post
        post_url = "https://api.linkedin.com/v2/ugcPosts"
        post_payload = {
            "author": f"urn:li:organization:{LINKEDIN_ORG}",
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": text},
                    "shareMediaCategory": "IMAGE",
                    "media": [{
                        "status": "READY",
                        "description": {"text": text},
                        "media": asset_urn,
                        "title": {"text": "New Podcast Episode"}
                    }]
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }

        share_res = requests.post(post_url, headers=headers, json=post_payload).json()
        print("✅ LinkedIn posted:", share_res)
    except Exception as e:
        print("❌ LinkedIn error:", e)

def post_to_pinterest(text, image_url):
    try:
        r = requests.post(ZAPIER_PINTEREST_WEBHOOK_URL, json={
            "text": text,
            "image_url": image_url
        })
        print("✅ Pinterest posted (via Zapier)")
    except Exception as e:
        print("❌ Pinterest error:", e)

### MAIN ROUTE ###
@app.route("/acast-webhook", methods=["POST"])
def acast_webhook():
    data = request.get_json()

    if data.get("event") != "episodePublished":
        return jsonify({"status": "ignored"}), 200

    title = data.get("title", "Untitled Episode")
    image_url = data.get("coverUrl", "")
    text = f"""🎙️ New Episode Out on *The Modern Space Race Podcast*!

🛰️ {title}

🎧 Listen here: https://shows.acast.com/tmhe-modern-space-rmodernspacerace"""

    # Post to all platforms
    post_to_twitter(text, image_url)
    post_to_facebook(text, image_url)
    post_to_instagram(text, image_url)
    post_to_linkedin(text, image_url)
    post_to_pinterest(text, image_url)

    return jsonify({"status": "posted"}), 200

@app.route("/")
def home():
    return "✅ Modern Space Race Webhook Running"

if __name__ == "__main__":
    app.run(debug=True)
