package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/signal"
	"strings"
	"syscall"

	"github.com/bwmarrin/discordgo"
	"github.com/joho/godotenv"
)

var (
	Token      string
	AIAgentURL string
)

type Message struct {
	Message string                 `json:"message"`
	Context map[string]interface{} `json:"context"`
}

type AIResponse struct {
	Status    string                 `json:"status"`
	Response  string                 `json:"response"`
	Context   map[string]interface{} `json:"context"`
	SessionID string                 `json:"session_id"`
	Bartender string                 `json:"bartender"`
}

func init() {
	err := godotenv.Load()
	if err != nil {
		log.Println("No .env file found, using environment variables")
	}
	Token = os.Getenv("DISCORD_TOKEN")
	AIAgentURL = os.Getenv("AI_AGENT_URL")
	if AIAgentURL == "" {
		AIAgentURL = "http://localhost:8000"
	}
}

func main() {
	dg, err := discordgo.New("Bot " + Token)
	if err != nil {
		log.Fatal("Error creating Discord session: ", err)
	}

	dg.AddHandler(messageCreate)
	dg.AddHandler(ready)

	// Add required intents
	dg.Identify.Intents = discordgo.IntentsGuildMessages |
		discordgo.IntentsMessageContent |
		discordgo.IntentsDirectMessages |
		discordgo.IntentsGuildMembers |
		discordgo.IntentsGuilds

	err = dg.Open()
	if err != nil {
		log.Fatal("Error opening connection: ", err)
	}

	log.Printf("🍺 Elsie the Holographic Bartender is now online! 🍺")
	log.Printf("Press CTRL-C to shut down the holographic matrix.")
	sc := make(chan os.Signal, 1)
	signal.Notify(sc, syscall.SIGINT, syscall.SIGTERM)
	<-sc

	dg.Close()
}

func ready(s *discordgo.Session, event *discordgo.Ready) {
	err := s.UpdateGameStatus(0, "🍺 Serving drinks across the galaxy")
	if err != nil {
		log.Println("Error setting status:", err)
	}
	log.Printf("Logged in as: %v#%v\n", s.State.User.Username, s.State.User.Discriminator)
}

func messageCreate(s *discordgo.Session, m *discordgo.MessageCreate) {
	// Enhanced mention detection
	mentioned := false
	content := strings.TrimSpace(m.Content)

	/* Debug logging
	log.Printf("DEBUG: ========= Message Details =========")
	log.Printf("DEBUG: From: %s (ID: %s)", m.Author.Username, m.Author.ID)
	log.Printf("DEBUG: Channel: %s", m.ChannelID)
	log.Printf("DEBUG: Raw Content: %q", m.Content)
	log.Printf("DEBUG: Mentions: %+v", m.Mentions)
	log.Printf("DEBUG: Role Mentions: %+v", m.MentionRoles)
	log.Printf("DEBUG: Bot ID: %s", s.State.User.ID)
	log.Printf("DEBUG: Bot Username: %s", s.State.User.Username)
	log.Printf("DEBUG: ================================")
	*/
	// Ignore own messages
	if m.Author.ID == s.State.User.ID {
		return
	}

	// Check if message is a DM
	isDM := m.GuildID == ""

	// Get basic channel info to determine if we should monitor all messages
	shouldMonitorAll := false
	if !isDM {
		// Try to get channel info to determine if this is a thread or special channel
		if channel, err := s.Channel(m.ChannelID); err == nil {
			// Monitor all messages in threads (where roleplay typically happens)
			isThread := channel.Type == discordgo.ChannelTypeGuildPublicThread ||
				channel.Type == discordgo.ChannelTypeGuildPrivateThread ||
				channel.Type == discordgo.ChannelTypeGuildNewsThread

			if isThread {
				shouldMonitorAll = true
				log.Printf("DEBUG: Thread detected (%s) - monitoring all messages", channel.Name)
			}

			// Also monitor channels with "rp" in the name
			if strings.Contains(strings.ToLower(channel.Name), "rp") ||
				strings.Contains(strings.ToLower(channel.Name), "roleplay") {
				shouldMonitorAll = true
				log.Printf("DEBUG: RP channel detected (%s) - monitoring all messages", channel.Name)
			}
		} else {
			// If we can't get channel info, log the error but continue
			log.Printf("DEBUG: Could not get channel info: %v", err)
		}
	}

	// Simple mention detection - if there are any mentions, process them
	if len(m.Mentions) > 0 || len(m.MentionRoles) > 0 {
		// Check user mentions
		for _, user := range m.Mentions {
			if user.ID == s.State.User.ID {
				mentioned = true
				log.Printf("DEBUG: Bot was mentioned via user mention!")
				break
			}
		}

		// Check role mentions
		if !mentioned && m.GuildID != "" {
			for _, roleID := range m.MentionRoles {
				guild, err := s.Guild(m.GuildID)
				if err != nil {
					log.Printf("DEBUG: Error getting guild info: %v", err)
					continue
				}
				for _, role := range guild.Roles {
					if role.ID == roleID && strings.EqualFold(role.Name, s.State.User.Username) {
						mentioned = true
						log.Printf("DEBUG: Bot was mentioned via role mention!")
						break
					}
				}
			}
		}
	}

	// Handle commands
	if strings.HasPrefix(content, "!elsie") {
		content = strings.TrimPrefix(content, "!elsie")
		content = strings.TrimSpace(content)
		if content == "" {
			content = "hello"
		}
		mentioned = true
		log.Printf("DEBUG: Command detected, content: %s", content)
	}

	// Determine if we should respond
	shouldRespond := mentioned || isDM || shouldMonitorAll

	// Only respond if mentioned, command used, in DM, or in a monitored channel
	if !shouldRespond {
		log.Printf("DEBUG: Message ignored - not mentioned, not DM, and not in monitored channel")
		return
	}

	// Log why we're responding
	if mentioned {
		log.Printf("DEBUG: Responding due to mention")
	} else if isDM {
		log.Printf("DEBUG: Responding due to DM")
	} else if shouldMonitorAll {
		log.Printf("DEBUG: Responding due to channel monitoring (thread/RP channel)")
	}

	// Clean up the content by removing mentions
	if mentioned {
		// Remove user mentions
		content = strings.ReplaceAll(content, fmt.Sprintf("<@%s>", s.State.User.ID), "")
		content = strings.ReplaceAll(content, fmt.Sprintf("<@!%s>", s.State.User.ID), "")
		// Remove role mentions that match the bot's name
		if m.GuildID != "" {
			guild, err := s.Guild(m.GuildID)
			if err == nil {
				for _, role := range guild.Roles {
					if strings.EqualFold(role.Name, s.State.User.Username) {
						content = strings.ReplaceAll(content, fmt.Sprintf("<@&%s>", role.ID), "")
					}
				}
			}
		}
		content = strings.TrimSpace(content)
		log.Printf("DEBUG: Content after removing mention: %s", content)
	}

	log.Printf("DEBUG: Processing message: %s", content)

	// Handle special Discord commands
	switch strings.ToLower(content) {
	case "ping":
		s.ChannelMessageSend(m.ChannelID, "🍺 *holographic matrix responds* Pong! All systems operational!")
		return
	case "help":
		helpMessage := `🍺 **ELSIE - HOLOGRAPHIC BARTENDER** 🍺

**Commands:**
• ` + "`!elsie [message]`" + ` - Chat with Elsie
• ` + "`@Elsie [message]`" + ` - Mention me to chat
• ` + "`!elsie menu`" + ` - View the galactic drink menu
• ` + "`!elsie help`" + ` - Show this help message
• ` + "`!elsie ping`" + ` - Test if I'm online

**Direct Messages:**
You can also chat with me privately by sending me a direct message! I'll respond to any message you send.

**Example Drinks to Order:**
• "Romulan Ale" - Blue and mysterious
• "Earl Grey Hot" - The Captain's favorite
• "Blood Wine" - For Klingon warriors
• "Synthehol" - No hangover guaranteed!

*I'm programmed with the finest bartending subroutines in the quadrant!*`
		s.ChannelMessageSend(m.ChannelID, helpMessage)
		return
	}

	// Send typing indicator
	s.ChannelTyping(m.ChannelID)

	// Process message through AI agent
	response := processWithAIEnhanced(content, s, m)

	// Send response
	if response != "" && response != "NO_RESPONSE" {
		s.ChannelMessageSend(m.ChannelID, response)
	} else if response == "NO_RESPONSE" {
		log.Printf("🤐 NO_RESPONSE received - Elsie is staying silent (DGM post or listening mode)")
		// Don't send any message - Elsie is intentionally staying quiet
	} else {
		s.ChannelMessageSend(m.ChannelID, "*holographic matrix flickers* My apologizes, but my processing subroutines are experiencing difficulties. Please try again later.")
	}
}

func processWithAI(content string, channelID string) string {
	log.Printf("⚠️  USING BASIC PROCESSING (no enhanced channel detection)")
	log.Printf("   📋 Channel ID: %s", channelID)

	// Create message payload
	message := Message{
		Message: content,
		Context: map[string]interface{}{
			"session_id": channelID, // Use channel ID as session ID
			"platform":   "discord",
		},
	}

	// Convert to JSON
	jsonData, err := json.Marshal(message)
	if err != nil {
		log.Printf("Error marshaling JSON: %v", err)
		return ""
	}

	// Make HTTP request to AI agent
	log.Printf("DEBUG: Sending basic request to %s with data: %s", AIAgentURL+"/process", string(jsonData))
	resp, err := http.Post(AIAgentURL+"/process", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		log.Printf("Error calling AI agent: %v", err)
		return ""
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Printf("Error reading response: %v", err)
		return ""
	}
	log.Printf("DEBUG: Received response: %s", string(body))

	// Parse AI response
	var aiResponse AIResponse
	err = json.Unmarshal(body, &aiResponse)
	if err != nil {
		log.Printf("Error unmarshaling AI response: %v", err)
		return ""
	}

	// Return the response if it exists (AI agent doesn't send status field)
	if aiResponse.Response != "" {
		return aiResponse.Response
	}

	return ""
}

func processWithAIEnhanced(content string, s *discordgo.Session, m *discordgo.MessageCreate) string {
	log.Printf("🔍 ATTEMPTING ENHANCED CHANNEL DETECTION:")
	log.Printf("   📋 Channel ID: %s", m.ChannelID)
	log.Printf("   🏰 Guild ID: %s", m.GuildID)

	// Get channel information
	channel, err := s.Channel(m.ChannelID)
	if err != nil {
		log.Printf("❌ ERROR getting channel info: %v", err)
		log.Printf("   🔄 Falling back to basic processing...")
		return processWithAI(content, m.ChannelID)
	}

	log.Printf("✅ CHANNEL INFO RETRIEVED:")
	log.Printf("   📛 Name: %s", channel.Name)
	log.Printf("   🏷️ Type: %v", channel.Type)
	log.Printf("   🆔 ID: %s", channel.ID)

	// Determine channel type and thread status
	isDM := m.GuildID == ""
	isThread := channel.Type == discordgo.ChannelTypeGuildPublicThread ||
		channel.Type == discordgo.ChannelTypeGuildPrivateThread ||
		channel.Type == discordgo.ChannelTypeGuildNewsThread

	channelType := "unknown"
	channelName := channel.Name

	// Map Discord channel types to our system
	switch channel.Type {
	case discordgo.ChannelTypeDM:
		channelType = "DM"
		isDM = true
		channelName = "DM"
		log.Printf("   💬 Detected as: Direct Message")
	case discordgo.ChannelTypeGuildText:
		channelType = "GUILD_TEXT"
		log.Printf("   📝 Detected as: Text Channel")
	case discordgo.ChannelTypeGuildVoice:
		channelType = "GUILD_VOICE"
		log.Printf("   🔊 Detected as: Voice Channel")
	case discordgo.ChannelTypeGuildPublicThread:
		channelType = "GUILD_PUBLIC_THREAD"
		isThread = true
		log.Printf("   🧵 Detected as: Public Thread")
	case discordgo.ChannelTypeGuildPrivateThread:
		channelType = "GUILD_PRIVATE_THREAD"
		isThread = true
		log.Printf("   🔒 Detected as: Private Thread")
	case discordgo.ChannelTypeGuildNewsThread:
		channelType = "GUILD_NEWS_THREAD"
		isThread = true
		log.Printf("   📰 Detected as: News Thread")
	case discordgo.ChannelTypeGuildNews:
		channelType = "GUILD_NEWS"
		log.Printf("   📰 Detected as: News Channel")
	case discordgo.ChannelTypeGuildStageVoice:
		channelType = "GUILD_STAGE_VOICE"
		log.Printf("   🎤 Detected as: Stage Channel")
	case discordgo.ChannelTypeGuildCategory:
		channelType = "GUILD_CATEGORY"
		log.Printf("   📁 Detected as: Category Channel")
	case discordgo.ChannelTypeGuildForum:
		channelType = "GUILD_FORUM"
		log.Printf("   💭 Detected as: Forum Channel")
	default:
		channelType = "UNKNOWN"
		log.Printf("   ❓ Unknown channel type: %v", channel.Type)
	}

	// Create enhanced message payload with channel context
	message := Message{
		Message: content,
		Context: map[string]interface{}{
			"session_id":   m.ChannelID,
			"platform":     "discord",
			"channel_id":   m.ChannelID,
			"channel_name": channelName,
			"channel_type": channelType,
			"is_dm":        isDM,
			"is_thread":    isThread,
			"guild_id":     m.GuildID,
			"user_id":      m.Author.ID,
			"username":     m.Author.Username,
		},
	}

	log.Printf("🌐 ENHANCED CHANNEL CONTEXT:")
	log.Printf("   📍 Channel: %s (%s)", channelName, channelType)
	log.Printf("   🧵 Is Thread: %v | 💬 Is DM: %v", isThread, isDM)
	log.Printf("   🆔 Channel ID: %s | Guild ID: %s", m.ChannelID, m.GuildID)
	log.Printf("   👤 User: %s (%s)", m.Author.Username, m.Author.ID)

	// Convert to JSON
	jsonData, err := json.Marshal(message)
	if err != nil {
		log.Printf("Error marshaling JSON: %v", err)
		return ""
	}

	// Make HTTP request to AI agent
	log.Printf("DEBUG: Sending enhanced request to %s", AIAgentURL+"/process")
	resp, err := http.Post(AIAgentURL+"/process", "application/json", bytes.NewBuffer(jsonData))
	if err != nil {
		log.Printf("Error calling AI agent: %v", err)
		return ""
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		log.Printf("Error reading response: %v", err)
		return ""
	}
	log.Printf("DEBUG: Received response: %s", string(body))

	// Parse AI response
	var aiResponse AIResponse
	err = json.Unmarshal(body, &aiResponse)
	if err != nil {
		log.Printf("Error unmarshaling AI response: %v", err)
		return ""
	}

	// Return the response if it exists
	if aiResponse.Response != "" {
		return aiResponse.Response
	}

	return ""
}
