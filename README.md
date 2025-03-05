<div align="center">
  <!-- <img src="https://github.com/user-attachments/assets/704e1568-5c42-4133-835b-2075fef6813b" width="300"/> -->
<img src="https://github.com/user-attachments/assets/704e1568-5c42-4133-835b-2075fef6813b" alt="Community Bot Logo" width="800"/>
</div>

# Credit Community Discord Server Bot


## Overview
This is a discord bot designed to be used for the Credit Community Discord server, servicing 7000 users and counting. The bot does various things 
The Credit Community Bot is a comprehensive Discord bot designed for the Credit Community Discord server, which currently serves over 7,000 users. It automates community management tasks, ensuring smooth operations, user verification, and content moderation while also delivering timely updates and managing premium membership features.

## Application Features
- **Referral Channel Management**: The bot tracks and enforces a 7-day cooldown period between each user's posts in the referral channel. Users who attempt to post more frequently will have their messages deleted, and they will receive a warning message.
- **Diamond Role Management**: The bot manages the Diamond role assignment for users with the Diamond Status role. This role is a paid tier in the discord server which services 100+ users. Users who do not meet the required activity level will have their Diamond role removed.
- **Activity-Based Access**: Users who send 25 or more messages in the server every 7 days have direct access to the full Diamond Membership, this data is stored in a JSON file with users unique account id's in order to keep track.
- **User Verification**: The bot posts a message in the rules channel, and users must react with a checkmark to receive the Verified role, this assists in parsing out any potential bots with malicious intent.
- **User Interaction**: Users can confirm their understanding of the server rules or ask for help through private messages with the bot. The bot will then assign roles or notify moderators accordingly.
- **RSS Feed Parser**: The bot uses a RSS feed parser thats works with finnance news websites and their API to parse through HTML and post it's news into discord channels through discord.Embeds so that users may see news in a pleasant embed.
- **Link Filtering**: The bot filters links for users who have just joined the server and continue to do so until the user reaches a certian messsage count and gains a "level role" which then stops the link filtering process. This is done in an attempt to stop fraudsters from joining and sending malicious links to the Community.
- **User-Based Commands**: The bot uses what is known as "slash commands" that work directly with discord's api and are directly built into users interfaces upon joining the credit community discord server, this works by typing "/" and seeing a list of commands that pop up for the user.
- **Persistent Data Storage**: The bot uses a JSON file to store data related to user messages and roles, ensuring consistency even if the bot goes offline.
## Technologies Used During Implemintation
- Amazon Web Services
- Python
- Discord API
- Github
- discord.py library
