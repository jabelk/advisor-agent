# Setting Up Claude Desktop

This page walks you through everything you need to get Claude connected to your Salesforce practice sandbox. You only need to do this once. It takes about 10 minutes.

## Step 1: Install Node.js

Claude Desktop needs a small helper program called Node.js to connect to Salesforce. Think of it like installing a driver for a printer — you do it once and forget about it.

1. Go to **[nodejs.org](https://nodejs.org/)**
2. Click the big green button that says **"LTS"** (it'll say something like "22.x.x LTS — Recommended For Most Users")
3. Download and run the installer
4. Click through the install wizard — just accept all the defaults and click "Next" until it's done

**How to check it worked**: Open **Terminal** (Mac) or **Command Prompt** (Windows) and type `node --version` then press Enter. You should see a version number like `v22.1.0`. If you see that, you're good — you can close Terminal.

> **Mac tip**: You can find Terminal by pressing Cmd+Space and typing "Terminal"
>
> **Windows tip**: Press the Windows key, type "cmd", and click "Command Prompt"

## Step 2: Install Claude Desktop

1. Go to **[claude.ai/download](https://claude.ai/download)**
2. Click the download button for your computer (Mac or Windows)
3. Install it like you would any other app (drag to Applications on Mac, or run the installer on Windows)
4. Open Claude Desktop
5. It'll ask you to sign in — create a free account with your email, or sign in if you already have one

**What you should see**: A chat screen where you can type messages to Claude, similar to ChatGPT.

## Step 3: Connect Claude to Your Salesforce Sandbox

This is the key step — it gives Claude the ability to look up clients, verify your work, and interact with your Salesforce practice data.

1. In Claude Desktop, look for your **profile icon** or a **gear icon** in the bottom-left corner and click it to open **Settings**
2. In the Settings window, click **"Developer"** on the left side
3. Click the button that says **"Edit Config"**
4. This opens a file — it might look empty or have some `{}` in it. **Select everything in the file and delete it**
5. Copy the entire block below (click on it, then Cmd+A to select all, Cmd+C to copy on Mac — or Ctrl+A, Ctrl+C on Windows):

```json
{
  "mcpServers": {
    "advisor-agent": {
      "command": "npx",
      "args": [
        "mcp-remote",
        "https://independent-acceptance-production-611a.up.railway.app/mcp",
        "--header",
        "Authorization: Bearer PASTE_YOUR_TOKEN_HERE"
      ]
    }
  }
}
```

6. Paste it into the file (Cmd+V on Mac, Ctrl+V on Windows)
7. Now find the text `PASTE_YOUR_TOKEN_HERE` in what you just pasted. Delete **only those words** and type (or paste) the token that was sent to you. Make sure:
   - The word `Bearer` and the space after it are still there
   - Your token is between the quote marks
   - It should look like: `"Authorization: Bearer your-token-goes-here"` (one long string, no spaces in the token itself)
8. Save the file (Cmd+S on Mac, Ctrl+S on Windows)
9. **Quit Claude Desktop completely** and reopen it (just closing the window isn't enough — on Mac, right-click the dock icon and click Quit)

**What you should see**: After reopening, look at the chat input area at the bottom. You should see a small **hammer icon** — that means the Salesforce tools are connected.

**If you don't see the hammer icon:**
- Double-check that you saved the file
- Make sure you fully quit and reopened Claude Desktop (not just closed the window)
- Make sure Node.js is installed (go back to Step 1)
- Make sure the token is correct — no extra spaces, and `Bearer ` (with a space) is still before the token

## Step 4: Test the Connection

Type this into Claude Desktop:

> How many clients are in my Salesforce sandbox?

**What you should see**: Claude will use a tool called `sandbox_list_clients` and tell you there are about 50 clients. If this works, you're all set!

**If Claude says it can't connect or doesn't use any tools:**
- Go back to Step 3 and double-check the config
- Try quitting and reopening Claude Desktop one more time
- If you're stuck, take a screenshot of what you see and send it over — we'll figure it out

## Step 5: Set Up the Tutor Project (Optional — Come Back Later)

This is optional. It turns Claude into a dedicated Salesforce tutor who knows the full lesson plan. You can skip this for now and come back after you've done a couple lessons.

1. Go to **[github.com/jabelk/advisor-agent](https://github.com/jabelk/advisor-agent)** in your browser
2. Click the green **"Code"** button near the top-right of the page
3. Click **"Download ZIP"**
4. Find the downloaded file (usually in your Downloads folder) and unzip it:
   - **Mac**: Double-click the .zip file
   - **Windows**: Right-click the .zip file and choose "Extract All"
5. Open the unzipped folder — inside you'll see a folder called **`guide`**. Remember where this is.
6. In Claude Desktop, click **"Projects"** in the left sidebar
7. Click the **+** button to create a new project
8. Name it **Salesforce Learning**
9. Click **"Add content"**, then **"Add folder"**
10. Browse to the **`guide`** folder from step 5 and select it
11. Start a new conversation inside this project and ask:

> What lessons are available?

**What you should see**: Claude lists all 6 lessons with descriptions. That means the tutor is set up and ready to guide you.

---

You're all set! Head back to the **[lesson table of contents](README.md)** and start with **[Lesson 0: Getting Started](00-getting-started.md)**.
