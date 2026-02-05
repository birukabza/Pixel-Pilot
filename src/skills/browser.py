import webbrowser


class BrowserSkill:
    def __init__(self):
        self.enabled = True
        print("Browser Skill: Enabled")

    def open_url(self, url):
        if not url:
            return "No URL provided"
        if not url.startswith("http"):
            url = "https://" + url
        try:
            webbrowser.open(url)
            return f"Opened {url}"
        except Exception as e:
            return f"Error opening URL: {e}"

    def search(self, query):
        if not query:
            return "No query provided"
        try:
            if "." in query and " " not in query:
                return self.open_url(query)

            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(url)
            return f"Searched Google for '{query}'"
        except Exception as e:
            return f"Error searching: {e}"
