
import grpc
import time
import grpcnewspubsub_pb2 as pb2
import grpcnewspubsub_pb2_grpc as pb2_grpc
import logging
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

def run():
    logging.basicConfig(level=logging.DEBUG)
    channel = grpc.insecure_channel('localhost:50051')
    stub = pb2_grpc.MsgServPubStreamSubUnaryStub(channel)

    # Subscribe to the server
    subscriber_id = f"subscriber-{int(time.time())}"  # Generate a unique subscriber ID
    request = pb2.SubscribeRequest(
        subscriber_id=subscriber_id,
        topics=["sports", "technology"]
    )

    print("Subscribing to the server...")

    logging.basicConfig(level=logging.DEBUG)
    print("Goint to call RPC... ")
    try:
        # Start receiving messages
        for response in stub.GetServerResponse(request):
            news_articles = NewsArticles(title=response.title,
                            description=response.description,
                            url=response.url,
                            published_at=response.published_at)
            print_news_articles_table(news_articles)


    except grpc.RpcError as e:
        print(f"Error occurred: {e}")

    except KeyboardInterrupt:
        print("Client interrupted and shutting down.")

    except Exception as e:
        print(f"Error while receiving streaming from publisher: {e}")
    finally:
        # Remove the subscriber if they disconnect
        print("In the finally block..")

if __name__ == '__main__':
    # Set the PYTHONIOENCODING environment variable to utf-8
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    run()
