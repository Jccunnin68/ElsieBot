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

	// Only respond if mentioned, command used, or in DM
	if !mentioned && !isDM {
		log.Printf("DEBUG: Message ignored - not mentioned and not DM")
		return
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
	response := processWithAI(content, m.ChannelID)

	// Send response
	if response != "" {
		s.ChannelMessageSend(m.ChannelID, response)
	} else {
		s.ChannelMessageSend(m.ChannelID, "*holographic matrix flickers* My apologizes, but my processing subroutines are experiencing difficulties. Please try again later.")
	}
}

func processWithAI(content string, channelID string) string {
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
	log.Printf("DEBUG: Sending request to %s with data: %s", AIAgentURL+"/process", string(jsonData))
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
