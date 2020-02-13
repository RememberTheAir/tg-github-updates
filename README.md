# Telegram GitHub updates bot

Simple bot designed to keep track of Telegram's GitHub repositories activity, and new Android betas published on HockeyApp. It can post to Telegram and Matrix.

### Running the bot

Install the requirements with `pip3 install -r requirements.txt`, and rename `config.example.toml` to `config.toml`.
Then open `config.toml` and change the values marked with "_CHANGEME_ ". Every key in this file is commented with a description.

The data about the tracked GitHub repositories is stored in `repos.default.toml`. This is a static file.
If you want to change this list, you can rename the file to `repos.toml` and edit it.
On startup, by default the bot will look for `repos.toml` and load it. If `repos.toml` does not exist, it will load `repos.default.toml` instead.

### Note about Matrix

Posting to a Matrix instance is something that has been added later, so it doesn't support the following things:

- sending releases' assets urls
- sending releases' assets files
- Telegram betas updates

Posting logic is a bunch of spaghetti code I put together to get the thing running as soon as possible, you're free to laugh at it.
