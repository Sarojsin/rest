import asyncio
from tools.browser import tabs, wait, snapshot

async def main():
    # Open admin login page
    tab = await tabs.open({"url": "http://127.0.0.1:5173/admin/login"})
    await wait({"tabID": tab["id"], "condition": "load", "timeoutMs": 8000})
    
    # Take snapshot and look for login form
    snap = await snapshot({"tabID": tab["id"]})
    content = snap.content or ""
    
    print("Login page found")
    print("Has email field:", "email" in content.lower())
    print("Has password field:", "password" in content.lower())
    print("First 300 chars:", content[:300])
    
    # Close the tab
    await tabs.close({"tabID": tab["id"]})

asyncio.run(main())