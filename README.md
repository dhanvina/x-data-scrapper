# X Post Details Fetcher 🐦

A streamlined Streamlit application for fetching and displaying X (formerly Twitter) post details with media support and local caching.

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![Streamlit](https://img.shields.io/badge/Streamlit-1.0+-red.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## 🌟 Features

- 📝 Fetch complete post details including text, metrics, and media
- 🖼️ Display images and videos from posts
- 📊 View engagement metrics (likes, retweets, quotes, replies)
- 💾 Local caching system to minimize API calls
- 📈 API usage tracking and quota management
- 👤 Author profile information display
- 📁 Save tweet data to text files
- ⚡ Rate limit handling with automatic retry

## 🚀 Getting Started

### Prerequisites

- Python 3.7 or higher
- Twitter API credentials (Basic tier access)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/xdata_extractor.git
cd xdata_extractor
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Configure your Twitter API credentials in `app.py`:
```python
API_KEY = "your_api_key"
API_SECRET = "your_api_secret"
ACCESS_TOKEN = "your_access_token"
ACCESS_TOKEN_SECRET = "your_access_token_secret"
BEARER_TOKEN = "your_bearer_token"
```

### Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser and navigate to `http://localhost:8501`

3. Enter a X post URL in the format: `https://x.com/username/status/123456789`

4. Click "Fetch Post Details" to retrieve the post information

## 📦 Project Structure

```
xdata_extractor/
├── app.py              # Main application file
├── README.md           # Project documentation
├── requirements.txt    # Python dependencies
├── tweet_cache/        # Cached tweet data
└── tweet_data.txt     # Saved tweet information
```

## 🔑 API Limits

- Basic tier Twitter API access (100 tweets per month)
- Automatic rate limit detection and handling
- Local caching to optimize API usage
- Monthly quota reset tracking

## 🛠️ Technical Details

### Components
- **Streamlit**: Web interface and data display
- **Tweepy**: Twitter API interaction
- **PIL**: Image processing
- **JSON**: Data caching and storage

### Features Implementation
- Automatic rate limit handling with countdown
- Local JSON-based tweet caching
- Structured data storage in text files
- Responsive media display
- API quota tracking and management

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

