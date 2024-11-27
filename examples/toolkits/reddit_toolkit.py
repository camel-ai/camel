# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ========= Copyright 2023-2024 @ CAMEL-AI.org. All Rights Reserved. =========

from camel.toolkits import RedditToolkit

reddit_toolkit = RedditToolkit()

# Example usage of collect_top_posts
subreddit_name = "python"
post_limit = 2
comment_limit = 3

print(f"Collecting top {post_limit} posts from r/{subreddit_name}...\n")
top_posts_data = reddit_toolkit.collect_top_posts(
    subreddit_name, post_limit, comment_limit
)

# Output the top posts data
for post in top_posts_data:
    print(f"Post Title: {post['Post Title']}")
    for comment in post["Comments"]:
        print(f"  Comment: {comment['Comment Body']}")
        print(f"  Upvotes: {comment['Upvotes']}")
    print()

'''
===============================================================================
Collecting top 2 posts from r/python...

Post Title: Lad wrote a Python script to download 
            Alexa voice recordings, 
            he didn't expect this email.
  Comment: I will be honest, I was expecting a Cease 
           and Desist from Amazon.
  Upvotes: 1857
  Comment: Very cool. That is the beauty of sharing. 
           You never know who or how it will help someone, 
           but you post it anyway because that is just being awesome. 

Thanks for sharing.
  Upvotes: 264
  Comment: This was posted publicly by [Michael Haephrati]
            (https://www.facebook.com/photo.php?fbid=10220524693682311)
            on Facebook.

Update: The lad is a Redditor! [**u/haephrati**]
        (https://www.reddit.com/user/haephrati/)

Update: The lad turned it into a [Software]
        (https://www.facebook.com/pg/accexa2020/about/?ref=page_internal)!
  Upvotes: 219

Post Title: This post has:
  Comment: scale tap piquant quiet advise salt languid abundant dolls long
           -- mass edited with redact.dev
  Upvotes: 1325
  Comment: Good job. But honestly, add a sleep timer of a few seconds. 
           This will eventually get your IP banned on reddit 
           if you bombard them with too many requests.
  Upvotes: 408
  Comment: Cool! Could you share it?
  Upvotes: 113
===============================================================================
'''

# Track keyword discussions
keywords = [
    "python",
    "programming",
    "coding",
    "software",
    "development",
    "machine learning",
    "artificial intelligence",
    "AI",
    "deep learning",
    "data science",
    "analytics",
    "automation",
    "tech",
    "technology",
    "engineering",
    "developer",
    "algorithm",
    "API",
    "framework",
    "library",
    "tool",
    "debug",
    "optimization",
    "performance",
    "security",
    "privacy",
    "database",
    "cloud",
    "server",
    "network",
    "startup",
    "entrepreneur",
    "innovation",
    "research",
    "science",
]

subreddits = [
    "python",
    "learnprogramming",
    "datascience",
    "machinelearning",
]
keyword_data = reddit_toolkit.track_keyword_discussions(
    subreddits, keywords, post_limit=2, comment_limit=5
)


# Perform sentiment analysis on collected data
sentiment_data = reddit_toolkit.perform_sentiment_analysis(keyword_data)

# Output the results
for item in sentiment_data:
    print(f"Subreddit: {item['Subreddit']}")
    print(f"Post Title: {item['Post Title']}")
    print(f"Comment Body: {item['Comment Body']}")
    print(f"Upvotes: {item['Upvotes']}")
    if 'Sentiment Score' in item:
        print(f"Sentiment Score: {item['Sentiment Score']}")
    print()

'''
===============================================================================

Subreddit: learnprogramming
Post Title: I ran a 100% free full stack web development bootcamp
            for those laid off by the pandemic. 
            65 people got jobs and we are doing it again! 
            I would love to have you join us!
Comment Body: If you want to learn to code, this will change your life.
Can't make it to class? Recorded classes are on Twitch and YouTube
Never touched code before? He starts from square 1!
Shy/introvert/don't like talking? Stick to the chat
Don't have support in real life? 
Join the discord and get more support and hype than your family
Don't have money? It's free!
Not in the US? Leon is Mr. Worldwide when it comes to teaching!
100Devs isn't just a free online bootcamp, 
it's a whole support network that will be there for you to cheer you on, 
help you out, and give you a shoulder to cry on. 
If you're on the fence, give it a try. You won't regret it.
Upvotes: 518
Sentiment Score: 0.385

Subreddit: learnprogramming
Post Title: I ran a 100% free full stack web development bootcamp 
            for those laid off by the pandemic. 
            65 people got jobs and we are doing it again! 
            I would love to have you join us!
Comment Body: If you need any free dev help let me know

I was also a teacher for 15 years before coding if that's helpful too
Upvotes: 533
Sentiment Score: 0.4

Subreddit: datascience
Post Title: data siens
Comment Body: I was once reading this article that went as: 
              "The AI already predicted how many goals Cavani 
              will score at Manchester United". 
It was a linear regression.
Upvotes: 345
Sentiment Score: 0.5

Subreddit: machinelearning
Post Title: [D] A Demo from 1993 of 32-year-old Yann LeCun 
            showing off the World's first Convolutional 
            Network for Text Recognition
Comment Body: The fact that they also had to know the 
              location of the numbers and that the algorithm 
              was robust to scale changes is impressive for 1993

It's not like they just solved MNIST in 1993, it's one step above that
Upvotes: 412
Sentiment Score: 0.5
===============================================================================
'''
