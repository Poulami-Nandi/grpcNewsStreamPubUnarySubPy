import grpc
from concurrent import futures
from threading import Thread, Lock
from newsapi import NewsApiClient
import time
import grpcnewspubsub_pb2_grpc as pb2_grpc
import grpcnewspubsub_pb2 as pb2
import traceback
import logging
import copy
import os

def get_dummy_news(topic):
    news_articles = {}
    news_articles["title"] = []
    news_articles["description"] = []
    news_articles["url"] = []
    news_articles["published_at"] = []
    for i in range(1,3):
        news_articles["title"].append(f"Dummy {i}-th title for {topic}");
        news_articles["description"].append(f"Dummy {i}-th description for {topic}");
        news_articles["url"].append(f"Dummy {i}-th url for {topic}");
        news_articles["published_at"].append(f"Dummy {i}-th published_at for {topic}");

    return news_articles;

def fetch_news_for_topics_from_global_ds(topics):
    """ fetch news for a given list of topics from all_news_articles dictionary """
    print(f"in function fetch_news_for_topics_from_global_ds {topics}")
    news_articles = {}
    news_articles["title"] = []
    news_articles["description"] = []
    news_articles["url"] = []
    news_articles["published_at"] = []

    logging.basicConfig(level=logging.DEBUG)
    if len(all_news_articles) != 0:
        for t in topics:
            # each news artile has title, published_at, url and description, so count of all those would be same
            news_articles["title"].extend(all_news_articles[t]["title"])
            news_articles["description"].extend(all_news_articles[t]["description"])
            news_articles["url"].extend(all_news_articles[t]["url"])
            news_articles["published_at"].extend(all_news_articles[t]["published_at"])
    else:
        news_articles["title"].append("ACK")
        news_articles["description"].append("ACK")
        news_articles["url"].append("ACK")
        news_articles["published_at"].append("ACK")

    #print(f"global DS news for {topics}: {news_articles}")
    return news_articles

def get_news_articles_for_topic(topic, news_api):
    """Fetches news articles for a given topic."""
    print(f"Fetching news for topic: {topic}")

    news_articles = {}
    news_articles["title"] = []
    news_articles["description"] = []
    news_articles["url"] = []
    news_articles["published_at"] = []

    try:
        # Fetch articles for the topic
        articles = news_api.get_everything(q=topic, language='en', sort_by='publishedAt', page_size=2)
        for article in articles.get('articles', []):
            #print(f"article is {article}");
            title = str(article.get('title', '')).encode('utf-8', errors='replace').decode('utf-8')
            description = str(article.get('description', '')).encode('utf-8', errors='replace').decode('utf-8')
            url = str(article.get('url', '')).encode('utf-8', errors='replace').decode('utf-8')
            published_at = str(article.get('publishedAt', '')).encode('utf-8', errors='replace').decode('utf-8')
            news_articles["title"].append(title);
            news_articles["description"].append(description);
            news_articles["url"].append(url);
            news_articles["published_at"].append(published_at);
    except Exception as e:
        print(f"Error fetching news for topic '{topic}': {e}")
        print(traceback.format_exc())  # Print full traceback for debugging
        news_articles = get_dummy_news(topic)

    return news_articles


class NewsProducerUnary(pb2_grpc.MsgServUnarySubServicer):
    def __init__(self, news_api):
        self.news_api = news_api;


    def GetServerResponse(self, request, context):
        print("inside function GetServerResponse of class NewsProducerUnary")
        # Ensure subscriber_id exists in the request
        subscriber_id = request.subscriber_id
        if not subscriber_id:
            print("Error: 'subscriber_id' is missing in the request.")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "subscriber_id is missing")

        print(f"Received subscription request from subscriber_id: {subscriber_id}")

        news_articles = {}
        news_articles["title"] = []
        news_articles["description"] = []
        news_articles["url"] = []
        news_articles["published_at"] = []
        print(f"Goint to fetch news for {subscriber_id} and topics {request.topics}")
        for t in request.topics:
            n = get_news_articles_for_topic(t, self.news_api);
            news_articles["title"].extend(n["title"])
            news_articles["description"].extend(n["description"])
            news_articles["url"].extend(n["url"])
            news_articles["published_at"].extend(n["published_at"])

        logging.basicConfig(level=logging.DEBUG)
        response = pb2.NewsArticle(
            title=news_articles["title"],
            description=news_articles["description"],
            url=news_articles["url"],
            published_at=news_articles["published_at"]
        )
        logging.info("Sending response: %s", response)
        return response


class NewsProducerStream(pb2_grpc.MsgServPubStreamSubUnaryServicer):
    def __init__(self, news_api):
        self.news_api = news_api;
        self.subscribers = {}  # Dictionary to store subscriber_id and their subscribed topics
        self.lock = Lock()

    def GetServerResponse(self, request, context):
        print("inside function GetServerResponse of class NewsProducerStream")
        # Ensure subscriber_id exists in the request
        subscriber_id = request.subscriber_id
        if not subscriber_id:
            print("Error: 'subscriber_id' is missing in the request.")
            context.abort(grpc.StatusCode.INVALID_ARGUMENT, "subscriber_id is missing")

        print(f"Received subscription request from subscriber_id: {subscriber_id}")

        with self.lock:
            # Initialize the subscriber's topic list if it doesn't exist
            if subscriber_id not in list(self.subscribers.keys()):
                self.subscribers[subscriber_id] = {"context" : context, "topics" : set()}
            self.subscribers[subscriber_id]["topics"].update(request.topics)
            print(f"Subscriber {subscriber_id} subscribed to topics: {request.topics}")


        while True:
            print(f"Goint to fetch news for {subscriber_id} and topics {request.topics}")
            news_articles = fetch_news_for_topics_from_global_ds(request.topics);

            logging.basicConfig(level=logging.DEBUG)
            response = pb2.NewsArticle(
                title=news_articles["title"],
                description=news_articles["description"],
                url=news_articles["url"],
                published_at=news_articles["published_at"]
            )
            logging.info("Sending response: %s", response)
            yield response  # Send the respinse to the client
            time.sleep(30)  # Wait for 30 seconds before sending the next article


    def fetch_news_for_subscriber_id(self, subscriber_id):
        """ fetch news for sub id """
        topics = []
        with self.lock:
            topics = self.subscribers[subscriber_id]["topics"]

        news_articles = {}
        news_articles["title"] = []
        news_articles["description"] = []
        news_articles["url"] = []
        news_articles["published_at"] = []
        if self.all_news_articles is not None:
            for t in topics:
                # each news artile has title, published_at, url and description, so count of all those would be same
                for item in self.all_news_articles[t]["title"]: #
                    news_articles["title"].append(item)
                for item in self.all_news_articles[t]["description"]: #
                    news_articles["description"].append(item)
                for item in self.all_news_articles[t]["url"]: #
                    news_articles["url"].append(item)
                for item in self.all_news_articles[t]["published_at"]: #
                    news_articles["published_at"].append(item)

        else:
            news_articles["title"].append("ACK")
            news_articles["description"].append("ACK")
            news_articles["url"].append("ACK")
            news_articles["published_at"].append("ACK")

        return news_articles

    def fetch_and_distribute_news(self):
        """Periodically fetch and distribute news articles to all subscribers."""
        subscribers_clone = {} # clone of subscribers dictionary
        all_topics = [] # complete list of topics for all subscribers
        while True:
            with self.lock:
                if not self.subscribers:
                    print("Subscribers list is empty now..")
                else:
                    ## copy from original subscribers dict
                    subscribers_clone = dict()
                    subscribers_clone = self.subscribers.copy()

            if subscribers_clone:
                all_topics = []
                #### make a list of unique topics
                for s in subscribers_clone.keys():
                    all_topics = list(set(all_topics) | set(subscribers_clone[s]["topics"]))

                for t in all_topics:
                    all_news_articles[t] = get_news_articles_for_topic(t, self.news_api)


            time.sleep(30)


def publisher_stream_server():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    news_api = NewsApiClient(api_key='ed5ef7e17b1f492d9ea657f0141e65f0')
    ## news producer generating unary news response for subscribers
    news_producer_unary = NewsProducerUnary(news_api=news_api)
    pb2_grpc.add_MsgServUnarySubServicer_to_server(news_producer_unary, server)
    ## news producer generating news stream for subscribers
    news_producer_stream = NewsProducerStream(news_api=news_api)
    pb2_grpc.add_MsgServPubStreamSubUnaryServicer_to_server(news_producer_stream, server)

    server.add_insecure_port('[::]:50051')
    server.start()
    print("Server started on port 50051.")

    # Start news fetching in a separate thread
    news_thread = Thread(target=news_producer_stream.fetch_and_distribute_news)
    news_thread.daemon = True
    news_thread.start()

    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == '__main__':
    # Set the PYTHONIOENCODING environment variable to utf-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    all_news_articles = {}
    publisher_stream_server()
