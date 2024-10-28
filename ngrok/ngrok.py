from pyngrok import ngrok

class NgrokLinkGenerator:
    def __init__(self, port=5000):
        self.port = port

    def generate_link(self):
        public_url = ngrok.connect(self.port, bind_tls=True)
        formatted_url = f"{public_url}/webhookcallback"
        print(f"URL pública para webhook '{formatted_url}'")
        return formatted_url

    def stop_ngrok(self):
        ngrok.disconnect(self.port)
        ngrok.kill()

if __name__ == "__main__":
    ngrokclient = NgrokLinkGenerator()
    ngrokclient.generate_link()
