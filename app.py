import streamlit as st
import tweepy
import re
import requests
import time
import json
import os
from datetime import datetime, timezone
from io import BytesIO
from PIL import Image

# Cache directory setup
CACHE_DIR = "tweet_cache"
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Streamlit app title
st.title("X Post Details Fetcher")

# Sidebar for cache management and stats
with st.sidebar:
    st.title("Cache and API Stats")
    
    # Cache management section
    st.subheader("Cache Management")
    if st.button("Clear Cache", key="clear_cache_button"):
        for file in os.listdir(CACHE_DIR):
            os.remove(os.path.join(CACHE_DIR, file))
        st.success("Cache cleared successfully!")
    
    # Show cached tweets count
    cached_tweets = len([f for f in os.listdir(CACHE_DIR) if f.endswith('.json')])
    st.info(f"Cached tweets: {cached_tweets}")

# Initialize session state for API usage tracking
if 'api_calls' not in st.session_state:
    st.session_state.api_calls = 0

def handle_rate_limit(error):
    """Handle rate limit errors by waiting and retrying"""
    if isinstance(error, tweepy.errors.TooManyRequests):
        reset_time = int(error.response.headers.get('x-rate-limit-reset', 0))
        current_time = int(time.time())
        sleep_time = max(reset_time - current_time, 0) + 1
        
        # Show waiting message with countdown
        wait_placeholder = st.empty()
        for remaining in range(sleep_time, 0, -1):
            wait_placeholder.info(f"Rate limit reached. Waiting {remaining} seconds before retrying...")
            time.sleep(1)
        wait_placeholder.empty()
        return True
    return False

def load_cached_tweet(tweet_id):
    """Load tweet from cache if it exists and convert to Tweepy Response format"""
    cache_file = os.path.join(CACHE_DIR, f"{tweet_id}.json")
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
                
            # Create a Tweet-like object that matches the structure Tweepy expects
            tweet_data = type('TweetData', (), {
                'data': cached_data['data'],
                'text': cached_data['data'].get('text', ''),
                'created_at': cached_data['data'].get('created_at', ''),
                'public_metrics': cached_data['data'].get('public_metrics', {})
            })
            
            return type('Response', (), {
                'data': tweet_data,
                'includes': cached_data['includes']
            })
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading cached tweet: {e}")
            # If there's an error with the cache file, remove it
            os.remove(cache_file)
            return None
    return None

def save_tweet_to_cache(tweet_id, tweet_data):
    """Save tweet data to cache"""
    # Convert datetime to string to make it JSON serializable
    if 'created_at' in tweet_data['data']:
        tweet_data['data']['created_at'] = str(tweet_data['data']['created_at'])
    
    cache_file = os.path.join(CACHE_DIR, f"{tweet_id}.json")
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(tweet_data, f, default=str)

def fetch_tweet_with_retry(client, tweet_id, max_retries=3):
    """Fetch tweet with automatic retry on rate limit and caching"""
    # Check cache first
    cached_data = load_cached_tweet(tweet_id)
    if cached_data:
        return cached_data
    
    # If not in cache, fetch from API
    st.session_state.api_calls += 1
    
    # Show current API usage
    quota_used = (st.session_state.api_calls / 100) * 100  # 100 is the monthly limit
    st.sidebar.metric("API Usage", f"{st.session_state.api_calls}/100 posts", f"{quota_used:.1f}%")
    
    # Calculate days until reset (resets on the 10th of each month)
    now = datetime.now(timezone.utc)
    if now.day > 10:
        next_reset = datetime(now.year, now.month + 1, 10, tzinfo=timezone.utc)
    else:
        next_reset = datetime(now.year, now.month, 10, tzinfo=timezone.utc)
    days_until_reset = (next_reset - now).days
    st.sidebar.info(f"API quota resets in {days_until_reset} days")
    
    # Check if we're about to exceed the limit
    if st.session_state.api_calls >= 100:
        st.error("Monthly API limit reached. Please try again next month.")
        return None
        
    for attempt in range(max_retries):
        try:
            response = client.get_tweet(
                tweet_id,
                expansions=["author_id", "attachments.media_keys", "referenced_tweets.id", "referenced_tweets.id.author_id"],
                tweet_fields=["created_at", "public_metrics", "conversation_id", "referenced_tweets"],
                user_fields=["username", "name", "profile_image_url", "description"],
                media_fields=["url", "type", "preview_image_url", "variants"]
            )
            
            if response.data:
                # Convert response data to JSON-serializable format
                referenced_tweets = []
                if hasattr(response.data, 'referenced_tweets') and response.data.referenced_tweets is not None:
                    referenced_tweets = [
                        {'type': t.type, 'id': t.id}
                        for t in response.data.referenced_tweets
                    ]
                
                cache_data = {
                    'data': {
                        'text': response.data.text,
                        'created_at': str(response.data.created_at),
                        'public_metrics': response.data.public_metrics,
                        'referenced_tweets': referenced_tweets
                    },
                    'includes': {
                        'users': [{
                            'username': user.username,
                            'name': user.name,
                            'profile_image_url': user.profile_image_url,
                            'description': user.description if hasattr(user, 'description') else None
                        } for user in response.includes['users']]
                    }
                }
                
                # Handle media if present
                if 'media' in response.includes:
                    cache_data['includes']['media'] = [{
                        'type': media.type,
                        'url': getattr(media, 'url', None),
                        'preview_image_url': getattr(media, 'preview_image_url', None),
                        'variants': [
                            {
                                'content_type': v.get('content_type', ''),
                                'url': v.get('url', ''),
                                'bit_rate': v.get('bit_rate', 0)
                            }
                            for v in (getattr(media, 'variants', []) or [])
                        ]
                    } for media in response.includes['media']]
                
                save_tweet_to_cache(tweet_id, cache_data)
                
                # Create a Response-like object
                return type('Response', (), {
                    'data': type('TweetData', (), {
                        'text': response.data.text,
                        'created_at': response.data.created_at,
                        'public_metrics': response.data.public_metrics
                    }),
                    'includes': cache_data['includes']
                })
            
            return response
            
        except tweepy.errors.TooManyRequests as e:
            if attempt < max_retries - 1 and handle_rate_limit(e):
                continue
            raise
        except Exception as e:
            raise

# Create a form for input
with st.form(key='post_form'):
    # Input for X post link
    post_link = st.text_input("Enter X Post Link (e.g., https://x.com/username/status/123456789):")
    submit_button = st.form_submit_button(label='Fetch Post Details')

# API credentials (store securely in production using st.secrets)
API_KEY = ""
API_SECRET = ""
ACCESS_TOKEN = ""
ACCESS_TOKEN_SECRET = ""
BEARER_TOKEN = ""
# Initialize Tweepy client
client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET
)

def extract_tweet_id(url):
    # Extract tweet ID from URL
    match = re.search(r'status/(\d+)', url)
    return match.group(1) if match else None

def save_to_file(tweet_data, filename="tweet_data.txt"):
    with open(filename, "a", encoding="utf-8") as f:
        f.write("\n" + "="*50 + "\n")
        f.write(f"Tweet ID: {tweet_data['id']}\n")
        f.write(f"Author: @{tweet_data['author']}\n")
        f.write(f"Posted: {tweet_data['created_at']}\n")
        f.write(f"Text: {tweet_data['text']}\n")
        f.write(f"Likes: {tweet_data['likes']}\n")
        f.write(f"Retweets: {tweet_data['retweets']}\n")
        f.write(f"Quote Count: {tweet_data['quote_count']}\n")
        f.write(f"Reply Count: {tweet_data['reply_count']}\n")
        f.write("="*50 + "\n")

if submit_button:
    try:
        # Extract tweet ID
        tweet_id = extract_tweet_id(post_link)
        if not tweet_id:
            st.error("Invalid X post link. Please ensure it contains a valid status ID.")
        else:
            with st.spinner('Fetching tweet details...'):
                # Use the new retry function
                tweet = fetch_tweet_with_retry(client, tweet_id)

                if tweet and tweet.data:
                    # Display tweet details
                    st.subheader("Post Details")
                    author = tweet.includes['users'][0]
                    
                    # Author info with profile image
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        response = requests.get(author['profile_image_url'])
                        profile_img = Image.open(BytesIO(response.content))
                        st.image(profile_img, width=100)
                    with col2:
                        st.write(f"**Name**: {author['name']}")
                        st.write(f"**Username**: @{author['username']}")
                        if author['description']:
                            st.write(f"**Bio**: {author['description']}")

                    st.write(f"**Text**: {tweet.data.text}")
                    st.write(f"**Posted**: {tweet.data.created_at}")
                    
                    # Metrics
                    metrics = tweet.data.public_metrics
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Likes", metrics['like_count'])
                    with col2:
                        st.metric("Retweets", metrics['retweet_count'])
                    with col3:
                        st.metric("Quotes", metrics['quote_count'])
                    with col4:
                        st.metric("Replies", metrics['reply_count'])

                    # Save data to file
                    tweet_data = {
                        'id': tweet_id,
                        'author': author['username'],
                        'text': tweet.data.text,
                        'created_at': tweet.data.created_at,
                        'likes': metrics['like_count'],
                        'retweets': metrics['retweet_count'],
                        'quote_count': metrics['quote_count'],
                        'reply_count': metrics['reply_count']
                    }
                    save_to_file(tweet_data)
                    st.success("Tweet data has been saved to tweet_data.txt")

                    # Display media (images/videos)
                    if "media" in tweet.includes:
                        st.subheader("Media")
                        for media in tweet.includes["media"]:
                            if media['type'] == "photo":
                                response = requests.get(media['url'])
                                img = Image.open(BytesIO(response.content))
                                st.image(img, caption="Image from post")
                            elif media['type'] == "video" or media['type'] == "animated_gif":
                                if media['variants']:
                                    # Find the MP4 variant with the highest bitrate
                                    mp4_variants = [v for v in media['variants'] if v['content_type'] == 'video/mp4']
                                    if mp4_variants:
                                        best_variant = max(mp4_variants, key=lambda x: x.get('bit_rate', 0))
                                        st.video(best_variant['url'])
                            # Fallback to preview image if video can't be displayed
                            if media['preview_image_url']:
                                st.image(media['preview_image_url'], caption="Video preview")
                    else:
                        st.write("No media attached to this post.")

                else:
                    st.error("Post not found or is private.")
    except tweepy.errors.TooManyRequests:
        st.error("Rate limit reached. Please try again later.")
    except tweepy.errors.NotFound:
        st.error("Tweet not found. The post might have been deleted or is private.")
    except tweepy.errors.Unauthorized:
        st.error("Authentication error. Please check your API credentials.")
    except Exception as e:
        st.error(f"Error fetching post: {str(e)}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            st.error(f"API Response: {e.response.text}")

# Instructions for users
st.markdown("""
### How to Use
1. Enter a valid X post link in the format `https://x.com/username/status/123456789`.
2. Ensure the post is public and the link is correct.
3. The app will display the post's text, author, metrics, and any attached images or video previews.
""")
