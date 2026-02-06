import streamlit as st
import requests
from datetime import datetime, timedelta

# YouTube API Key 
API_KEY = "AIzaSyDHE3DYw9DKpBDvW1ijAs_IwCzCz6XKcNM"

YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
YOUTUBE_VIDEO_URL = "https://www.googleapis.com/youtube/v3/videos"
YOUTUBE_CHANNEL_URL = "https://www.googleapis.com/youtube/v3/channels"

# Streamlit App Title
st.title("YouTube Viral Topics Tool")

# 1) Days input
days = st.number_input(
    "Enter Days to Search (1-30):",
    min_value=1,
    max_value=30,
    value=5
)

# 2) Subscriber limit input
subscriber_limit = st.number_input(
    "Max Subscriber Count (channels below this will be included):",
    min_value=0,
    value=5000
)

# 3) Number of results to return
num_results = st.number_input(
    "Number of Results to Return:",
    min_value=1,
    max_value=50,
    value=10
)

# 4) Keywords input box (Niche Finder Keywords)
keywords_input = st.text_area(
    "Paste Niche Finder Keywords (comma-separated):",
    value=""
)

# ⭐ NEW: Additional Relevant Keywords input box
additional_keywords_input = st.text_area(
    "Add Your Own Relevant Keywords (comma-separated) - Optional:",
    value="",
    help="Add extra keywords to improve results. These will be searched along with niche finder keywords."
)

# Convert pasted text into lists
niche_keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
additional_keywords = [k.strip() for k in additional_keywords_input.split(",") if k.strip()]

# ⭐ Combine both keyword lists
keywords = niche_keywords + additional_keywords

# Fetch Data Button
if st.button("Fetch Data"):
    try:
        # Basic validation
        if not keywords:
            st.warning("Please paste at least 1 keyword (niche finder or additional keywords).")
        else:
            st.info(f"Searching {len(niche_keywords)} niche finder keywords + {len(additional_keywords)} additional keywords = {len(keywords)} total")
            
            # Calculate date range
            start_date = (datetime.utcnow() - timedelta(days=int(days))).isoformat("T") + "Z"
            all_results = []

            # Iterate over the list of keywords
            for keyword in keywords:
                st.write(f"Searching for keyword: {keyword}")

                # Define search parameters (request more to filter later)
                search_params = {
                    "part": "snippet",
                    "q": keyword,
                    "type": "video",
                    "order": "viewCount",
                    "publishedAfter": start_date,
                    "maxResults": 50,  # Get more results to filter by subscriber count
                    "key": API_KEY,
                }

                # Fetch video data
                response = requests.get(YOUTUBE_SEARCH_URL, params=search_params)
                data = response.json()

                # Check if "items" key exists
                if "items" not in data or not data["items"]:
                    st.warning(f"No videos found for keyword: {keyword}")
                    continue

                videos = data["items"]

                video_ids = [
                    video["id"]["videoId"]
                    for video in videos
                    if "id" in video and "videoId" in video["id"]
                ]

                if not video_ids:
                    st.warning(f"Skipping keyword: {keyword} due to missing video data.")
                    continue

                # Fetch video statistics
                stats_params = {"part": "statistics", "id": ",".join(video_ids), "key": API_KEY}
                stats_response = requests.get(YOUTUBE_VIDEO_URL, params=stats_params)
                stats_data = stats_response.json()

                if "items" not in stats_data or not stats_data["items"]:
                    st.warning(f"Failed to fetch video statistics for keyword: {keyword}")
                    continue

                # Create a lookup dictionary: video_id -> video stats
                video_stats_map = {
                    item["id"]: item["statistics"]
                    for item in stats_data["items"]
                }

                # Get unique channel IDs
                channel_ids = list(set([
                    video["snippet"]["channelId"]
                    for video in videos
                    if "snippet" in video and "channelId" in video["snippet"]
                ]))

                # Fetch channel statistics
                channel_params = {"part": "statistics", "id": ",".join(channel_ids), "key": API_KEY}
                channel_response = requests.get(YOUTUBE_CHANNEL_URL, params=channel_params)
                channel_data = channel_response.json()

                if "items" not in channel_data or not channel_data["items"]:
                    st.warning(f"Failed to fetch channel statistics for keyword: {keyword}")
                    continue

                # Create a lookup dictionary: channel_id -> subscriber count
                channel_subs_map = {
                    item["id"]: int(item["statistics"].get("subscriberCount", 0))
                    for item in channel_data["items"]
                }

                # Collect results with correct mapping
                for video in videos:
                    video_id = video["id"]["videoId"]
                    channel_id = video["snippet"]["channelId"]
                    
                    title = video["snippet"].get("title", "N/A")
                    description = video["snippet"].get("description", "")[:200]
                    video_url = f"https://www.youtube.com/watch?v={video_id}"

                    # Get views from video stats map
                    views = int(video_stats_map.get(video_id, {}).get("viewCount", 0))
                    
                    # Get subscriber count from channel map
                    subs = channel_subs_map.get(channel_id, 0)

                    # Filter by subscriber count
                    if subs < int(subscriber_limit):
                        all_results.append({
                            "Title": title,
                            "Description": description,
                            "URL": video_url,
                            "Views": views,
                            "Subscribers": subs,
                            "Channel_ID": channel_id  # For debugging
                        })

            # Sort by views (descending) and limit results
            all_results = sorted(all_results, key=lambda x: x["Views"], reverse=True)[:int(num_results)]

            # Display results
            if all_results:
                st.success(f"Found {len(all_results)} results matching your criteria!")
                for idx, result in enumerate(all_results, 1):
                    st.markdown(
                        f"### {idx}. {result['Title']} \n"
                        f"**Description:** {result['Description']} \n"
                        f"**URL:** [Watch Video]({result['URL']}) \n"
                        f"**Views:** {result['Views']:,} \n"
                        f"**Subscribers:** {result['Subscribers']:,}"
                    )
                    st.write("---")
            else:
                st.warning(f"No results found for channels with fewer than {int(subscriber_limit):,} subscribers.")

    except Exception as e:
        st.error(f"An error occurred: {e}")
