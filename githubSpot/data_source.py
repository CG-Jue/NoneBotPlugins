

import aiohttp


headers = {"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"}

async def get_github_reposity_information(url: str) -> str:
    try:
        UserName, RepoName = url.replace("https://github.com/", "").split("/")
    except:
        UserName, RepoName = url.replace("github.com/", "").split("/")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://api.github.com/users/{UserName}", headers=headers, timeout=5) as response:
            RawData = await response.json()
            AvatarUrl = RawData["avatar_url"]
            ImageUrl = f"https://socialify.git.ci/{UserName}/{RepoName}/png?description=1&font=Rokkitt&forks=1&issues=1&language=1&name=1&owner=1&pattern=Circuit%20Board&pulls=1&stargazers=1&theme=Light&logo={AvatarUrl}"

            return ImageUrl