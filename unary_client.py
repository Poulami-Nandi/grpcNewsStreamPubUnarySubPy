import grpc
import grpcnewspubsub_pb2_grpc as pb2_grpc
import grpcnewspubsub_pb2 as pb2
import time
from tabulate import tabulate
import os

# There are 4 elements in news article title, description, published_at and url
class NewsArticles:
    def __init__(self, title, description, url, published_at):
        self.title = title
        self.description = description
        self.url = url
        self.published_at = published_at

def print_news_articles_table(news_articles):
    # Create a list of rows where each row corresponds to a news article
    table_data = []
    for i in range(len(news_articles.title)):
        row = [
            news_articles.title[i],
            news_articles.description[i],
            news_articles.url[i],
            news_articles.published_at[i]
        ]
        table_data.append(row)

    # Define the table headers
    headers = ['Title', 'Description', 'URL', 'Published At']

    # Print the table
    print(f"Fetched fresh news at {time.time()}")
    print(tabulate(table_data, headers=headers, tablefmt="fancy_grid", showindex=True))

class UnaryClient(object):
    """
    Client for gRPC functionality
    """

    def __init__(self):
        self.host = 'localhost'
        self.server_port = 50051

        # instantiate a channel
        self.channel = grpc.insecure_channel(
            '{}:{}'.format(self.host, self.server_port))

        # bind the client and the server
        self.stub = pb2_grpc.MsgServUnarySubStub(self.channel)

    def get_url(self, message):
        """
        Client function to call the rpc for GetServerResponse
        """
        message = pb2.Message(message=message)
        print(f'{message}')
        return self.stub.GetServerResponse(message)


if __name__ == '__main__':
    # Set the PYTHONIOENCODING environment variable to utf-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    client = UnaryClient()

    # Establish a connection to the gRPC server
    with grpc.insecure_channel('localhost:50051') as channel:
        stub = pb2_grpc.MsgServUnarySubStub(channel)
        # Request topics to subscribe
        topics = input("Enter the topics you want to subscribe to (comma-separated): ").split(',')
        topics = [topic.strip() for topic in topics]  # Clean up whitespace

        # Subscribe to the news service
        subscriber_id = f"subscriber-{int(time.time())}"  # Generate a unique subscriber ID
        print("sub id is: ", subscriber_id);
        print(f"Subscribed to topics: {topics}")
        response = stub.GetServerResponse(pb2.SubscribeRequest(subscriber_id = subscriber_id, topics=topics))
        news_articles = NewsArticles(title=response.title,
                        description=response.description,
                        url=response.url,
                        published_at=response.published_at)
        print_news_articles_table(news_articles)
