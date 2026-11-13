# Noviokro v0.9.0 GUI/NUI Additive Development Update

Based on the user-provided v0.8.0 standalone archive. Original source files and earlier releases are not overwritten. All original backend files and routes are preserved unchanged.

## Implemented
- React feature-status navigation for existing and planned modules.
- Natural-language **typed** command interpreter for read-only navigation.
- Optional Web Speech API voice input where supported, requiring user microphone permission. Browser speech services may process voice remotely.
- High-contrast, large-text, keyboard focus indicators, aria-live command feedback, responsive layout, skip link.
- Original existing React App, V07Panel and V08Panel retained below the new console.

## Not implemented / not claimed
- Universal offline speech recognition, voice execution of API actions, fully accessible NUI certification.
- New production-ready gateway, live application integrations, new custom discovery backend, complete DevBot or CallBot.
- Production security review.

## Start
Run the existing Docker Compose setup per README_V08.md, or from dashboard: `npm install && npm run dev`. Visit http://127.0.0.1:3000. No new backend environment variables are required.

## Safety
Commands only navigate the interface. They cannot send API requests, scan endpoints, modify records or execute bots. Do not dictate credentials into browser speech recognition.
