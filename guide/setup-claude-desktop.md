# Setting Up Claude Desktop

This page walks you through installing Claude Desktop and connecting it to the Salesforce sandbox tools. You only need to do this once.

## Step 1: Download Claude Desktop

Go to **[claude.ai/download](https://claude.ai/download)** and download the version for your computer (Mac or Windows). Install it like you would any app.

Open it and create a free account (or sign in if you have one).

## Step 2: Connect to the Salesforce Tools

This step tells Claude Desktop how to talk to your Salesforce sandbox. You'll paste a small config into Claude's settings.

1. Open Claude Desktop
2. Go to **Settings** (click your name or the gear icon in the bottom-left)
3. Click **"Developer"** in the left sidebar
4. Click **"Edit Config"** — this opens a JSON file in your text editor
5. Replace everything in that file with the following:

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

6. Replace `PASTE_YOUR_TOKEN_HERE` with the token that was sent to you (keep the word `Bearer` and the space before the token)
7. Save the file and **restart Claude Desktop**

> **Note**: You need Node.js installed for the `npx` command to work. If you don't have it, download it from [nodejs.org](https://nodejs.org/) — grab the LTS version and install it with all the defaults.

## Step 3: Verify It Works

After restarting Claude Desktop, you should see a small **hammer icon** in the chat input area. That means the tools are connected.

Try typing:

> "How many clients are in my Salesforce sandbox?"

If Claude responds with a list of about 50 clients, you're all set.

**If it doesn't work:**
- Make sure you saved the config file and restarted Claude Desktop
- Make sure the token is correct (no extra spaces, no quotes around it beyond what's already there)
- Make sure Node.js is installed (open Terminal or Command Prompt and type `node --version` — you should see a version number)

## Step 4: Set Up the Tutor Project (Optional)

This is optional but gives you a better experience. It turns Claude into a dedicated Salesforce tutor that knows the lesson plan.

1. Download the guide files to your computer:
   - Go to **[github.com/jabelk/advisor-agent](https://github.com/jabelk/advisor-agent)**
   - Click the green **"Code"** button
   - Click **"Download ZIP"**
   - Unzip it somewhere you'll remember (Desktop or Documents is fine)
2. In Claude Desktop, click **"Projects"** in the left sidebar
3. Click the **+** button to create a new project
4. Name it **"Salesforce Learning"**
5. Click **"Add content"** and then **"Add folder"**
6. Navigate to the unzipped folder and select the **`guide`** folder inside it
7. Start a new conversation in this project

Try asking:

> "What lessons are available?"

Claude should list all 6 lessons with descriptions. That means the tutor is working.

---

Once you're set up, head back to the [lesson table of contents](README.md) and start with Lesson 0.
