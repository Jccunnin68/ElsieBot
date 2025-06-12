# DGM Controls & Guide

This guide is for Deputy Game Masters (DGMs) and explains how to use the special `[DGM]` commands to control scenes, characters, and Elsie's behavior.

## The `[DGM]` Tag

All DGM commands must start with the `[DGM]` tag at the beginning of the message. This tag is case-insensitive (e.g., `[dgm]` also works).

The `[DGM]` tag signals to Elsie that the message is a command from a game master and should be treated with special priority.

### Key Behaviors of DGM Posts

-   **No Response**: Elsie will **never** respond to a DGM post. She will process the command silently in the background.
-   **Channel Override**: DGM posts work in **any** channel. You can use them to start or end a roleplay scene even in channels where roleplay is normally restricted (like a general chat channel).
-   **Roleplay Session Control**: DGM posts are the primary way to start and end official roleplay sessions.

## Scene Control Commands

### Starting a Scene

To start a new roleplay scene, simply begin your post with `[DGM]`. This will automatically initiate a new roleplay session.

**Example:**
```
[DGM] The doors to the bar slide open, revealing a dusty traveler. *John steps inside, his eyes adjusting to the dim light.* He makes his way to an empty table.
```

When Elsie sees this, she will:
1.  Start a new roleplay session.
2.  Enter "passive monitoring" mode, aware of the scene but not participating yet.
3.  Detect any characters mentioned in the post (e.g., `*John*` or `[Jane]`).

### Ending a Scene

To end a roleplay session, use `[DGM]` followed by a recognized end-of-scene command.

**Primary Command:**
-   `[DGM][END]`

**Other Supported Commands (Case-Insensitive):**
-   `[DGM] *end scene*`
-   `[DGM] *scene ends*`
-   `[DGM] *fade to black*`
-   `[DGM] *roll credits*`
-   `[DGM] *curtain falls*`
-   `[DGM] *the end*`
-   `[DGM] end of scene`
-   `[DGM] scene complete`

When Elsie sees an end-scene command, she will immediately terminate the roleplay session, clear all participant data, and return to her normal, non-roleplay state.

## Character Detection in DGM Posts

When you start a scene, Elsie will automatically detect character names to add them to her list of active participants. She recognizes characters in two formats:

1.  **Bracketed Names**: `[Character Name]`
    -   This is the preferred method for clarity.
    -   It supports multi-word names (e.g., `[Jane Smith]`).
2.  **Italicized Names (within emotes)**: `*Character Name*`
    -   Elsie will identify capitalized words within italicized text (`*...*`) as potential character names.

**Example of Character Detection:**
```
[DGM] *A lone figure named Fallo enters the bar.* [Maeve] looks up from her drink.
```
In this post, Elsie will automatically detect and track both **Fallo** and **Maeve**.

## Controlling Elsie Directly

You can directly control Elsie's actions and dialogue from a DGM post. This is useful for having Elsie perform a specific action that is critical to the scene.

To control Elsie, use the `[DGM][Elsie]` tag.

**Example:**
```
[DGM][Elsie] *She notices the new arrival and approaches the table.* "Welcome to the Ten Forward. What can I get for you, traveler?"
```

When Elsie sees this:
1.  She will **not** say or do anything herself.
2.  She will understand that the DGM has dictated her actions and dialogue.
3.  She will incorporate this action into her memory of the conversation, understanding that this is what she "did" in that turn.
4.  The roleplay session will continue, and she will be ready to respond to the next user message based on this new context.

This feature gives DGMs complete control over the narrative, ensuring Elsie's actions align perfectly with the needs of the story. 