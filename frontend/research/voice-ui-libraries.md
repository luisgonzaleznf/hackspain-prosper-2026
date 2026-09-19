# Voice UI Libraries for Telephone Agent Dashboards

## Executive Summary

- **Best Overall Fit**: LiveKit Agents UI is the strongest match for this hackathon because it combines media controls, session controls, audio visualizers, and transcripts, while LiveKit Telephony can route inbound SIP calls into rooms. The key decision is to use LiveKit for the call transport and its UI registry for the observer surface, not to treat a browser microphone as the telephone integration. [17] [17] [6]
- **Best Pipecat-Native Choice**: Pipecat Voice UI Kit is the broadest copy-in toolkit among the candidates. It includes conversation, transcript, session, audio-control, device, DTMF, thinking, and video components, plus configurable templates and SmallWebRTC transport support. Choose it when the backend is already Pipecat; SmallWebRTC alone is a browser transport, not a phone carrier bridge. [16] [16] [16]
- **Best Audio-Focused Collection**: ElevenLabs UI has the clearest catalog of purpose-built audio and voice surfaces: orb, bar visualizer, live waveform, matrix, mic selector, voice picker, voice button, transcript viewer, audio player, and conversation components. It is a strong visual layer, but the repository and docs do not by themselves provide inbound telephone orchestration. [18] [20]
- **Best Provider-Neutral Orb**: orb-ui is a focused React voice-agent layer rather than a complete component system. Its adapters cover Vapi, ElevenLabs, LiveKit, Pipecat, OpenAI Realtime, and Gemini Live, with controlled mode for custom stacks. It is an excellent companion for a call-state hero panel, but not enough for a full observer dashboard. [7] [10] [10]
- **Best General Voice Control**: assistant-ui supplies a reusable control bar and animated orb through a `RealtimeVoiceAdapter`, including connect, mute, disconnect, status, and volume state. It works with adapters such as LiveKit and ElevenLabs, but its center of gravity remains an AI chat frontend rather than a telephone operations console. [19] [19]
- **Provider Lock-In Warning**: Deepgram UI is a polished shadcn/Tailwind React collection, but its components are documented around Deepgram Voice Agent and its `@deepgram/react` hooks. Hume's official material is primarily EVI APIs, SDKs, and quickstarts, not a reusable multi-component UI library. [8] [15] [11] [11]
- **Observer-Dashboard Requirement**: A browser-side mic button can show the observer's own microphone state, but it cannot see an inbound telephone call unless the backend exposes call state, transcript events, and permitted audio or audio-derived levels. LiveKit's official telephony and observability material makes that separation explicit: phone calls are routed into rooms, while session insights contain transcripts, audio recordings, traces, and logs. [6] [13]
- **Top Three Choices**: Pick LiveKit Agents UI for the most integrated telephone path, Pipecat Voice UI Kit for a Pipecat-first implementation with source ownership, and ElevenLabs UI for the richest audio component palette. Add orb-ui or assistant-ui selectively rather than replacing the primary transport-aware layer.

## What Counts as a Voice UI Library

The useful distinction is between a component collection and the infrastructure that makes a voice session exist. A real reusable voice UI library should provide visible frontend surfaces such as a voice orb, audio-reactive visualization, waveform, microphone or speaker controls, call-state controls, transcript rendering, audio playback, voice selection, or an agent session panel. It should also expose source code or a package that can be styled and composed in an existing React application.

A registry model is especially relevant here. ElevenLabs UI, LiveKit Agents UI, Deepgram UI, and Vercel AI Elements use shadcn-style installation patterns in which components are added to the application codebase rather than consumed as an opaque hosted widget. LiveKit explicitly says its components are installed through a shadcn registry and leave full source in `components/agents-ui`; ElevenLabs exposes an official CLI for adding individual components. [17] [18] This is closer to the requested shadcn/ui, Beautiful UI, or Rare UI model than a backend SDK with a demo page.

The classification matters because several projects combine UI with transport logic. Pipecat's kit deliberately supports both connected components and headless variants, while Deepgram's UI is coupled to Deepgram Agent hooks. Those are still useful, but they should be evaluated as UI plus integration assumptions, not as provider-neutral visual primitives. [16] [15]

| Candidate | Actual UI inventory | Installation and ownership | License and verifiable repository signal | Provider and scope assessment |
|---|---|---|---|---|
| LiveKit Agents UI | IO/session controls, bar/grid/radial/wave/aura visualizers, chat transcript and indicator [17] | shadcn registry; copied into `components/agents-ui` [17] | Official `livekit/components-js`; Apache-2.0, 462 stars, 1,341 commits in the fetched repository page [21] | Best complete voice-agent surface when using LiveKit primitives |
| Pipecat Voice UI Kit | Conversation, transcript, session info, audio controls, connect, DTMF, thinking, device controls, text input, video/screen controls [16] | npm package, connected or headless components, configurable templates [16] | Official `pipecat-ai/voice-ui-kit`; BSD-2-Clause, 406 stars, 553 commits in the fetched page [4] | Broad and customizable, but Pipecat-oriented |
| ElevenLabs UI | Audio player, bar visualizer, conversation, live waveform, matrix, mic selector, orb, transcript viewer, voice button, voice picker, waveform [18] | Official CLI adds source components to the app [18] | Official `elevenlabs/ui`; MIT, 2,390 stars, 66 commits in the fetched page [20] | Strong audio catalog; transport and telephony remain application responsibilities |
| orb-ui | Orb themes, status states, audio-reactive signal, provider adapters, and accessible controls [7] [10] | `npm install orb-ui`; provider wrappers are separate [10] | Official `alexanderqchen/orb-ui`; MIT, 61 stars, 140 commits in the fetched page [10] | Focused orb/state library, not a full dashboard |
| Deepgram UI | Orb, voice button, conversation, text input, mic/speaker buttons, start button, status, mic selector, response, bar visualizer, waveform [15] | shadcn copy-in or `@deepgram/ui` package [8] [8] | Official UI link and MIT package/repository evidence [8] [15] | Polished, but documented around Deepgram Voice Agent |

The table suggests a practical rule: use a full registry when the dashboard needs several coordinated surfaces, then add a focused orb or audio component only where it improves the experience. Do not select a project merely because its README contains the words voice or agent; verify that it actually ships the UI primitives the application needs.

## Best Full Libraries in Detail

### 1. LiveKit Agents UI: strongest telephone-oriented foundation

LiveKit Agents UI is the most complete match for the requested observer console. Its official reference describes a library built on shadcn/ui and AI Elements for LiveKit's realtime platform, with pre-built controls for IO, sessions, transcripts, and audio visualization. The documented categories include `AgentControlBar`, track controls and toggles, disconnect and start-audio controls, five visualizer styles, `AgentChatTranscript`, and `AgentChatIndicator`. [17] [17]

Its installation model is unusually useful for a hackathon. The shadcn CLI adds the `@agents-ui` registry, individual components can be installed separately, and an all-components command is available. The resulting source is placed in the application and can be customized rather than hidden behind a hosted component package. [17] This matches the desired design workflow: start with polished defaults, then change typography, colors, layout, and call-state semantics locally.

The important case study is the relationship between the UI and LiveKit Telephony. LiveKit's official inbound-call workflow accepts calls, routes them to LiveKit rooms, configures inbound trunks and dispatch rules, and adds callers as SIP participants. [6] That means the same room/session model can feed a receptionist dashboard while the agent handles the phone caller. The frontend still needs application-level event mapping, but the transport architecture is aligned with the use case instead of being limited to browser capture.

For maturity evidence, the fetched official `livekit/components-js` page identified the repository as open source, Apache-2.0 licensed, with 462 stars, 170 forks, and 1,341 commits at the time of retrieval. Those are repository-page observations, not a claim that they remain current. [21] The library also has lower-level React components and hooks, so a team can drop below Agents UI when the observer view needs custom room, participant, or track behavior. [17]

**Decision**: choose LiveKit Agents UI as the default if the team wants the shortest path from inbound telephone call to a live observer view. Its main trade-off is platform coupling: the polished agent primitives assume LiveKit session and media concepts, so a Twilio-, Pipecat-, or custom-media backend will require an adapter layer or a different primary library.

### 2. Pipecat Voice UI Kit: broadest source-owned toolkit

Pipecat Voice UI Kit has the broadest explicit inventory among the candidates. The official component index lists bot audio control, bot volume, client status, connect, conversation, DTMF keypad, function-call content, device selection, message primitives, session information, text input, thinking, transcript overlay, user audio controls, screen and video controls, and related application primitives. [16] This is especially valuable for a receptionist prototype because DTMF, status, transcript, and session information are more operationally relevant than a decorative orb alone.

It also offers configurable templates. The official documentation describes templates as fully featured UIs composed from the core components and usable as-is or as a starting point; the listed templates include Console and Widget. [16] This is a better starting point for an observer dashboard than a single conversation button. The kit supports connected Pipecat components as well as headless components, has minimal dependencies, avoids framework-specific code, and is built on Tailwind 4 and shadcn primitives. [16]

The SmallWebRTC detail needs careful treatment. The quickstart installs the UI package, Pipecat client packages, and one transport package. The documented choices include `@pipecat-ai/small-webrtc-transport`, Daily, WebSocket, and MoQ transports. [16] SmallWebRTC is therefore a browser or realtime transport option in the Pipecat stack. It does not, by itself, provide a telephone number, carrier ingress, SIP trunk, or call-routing system. For inbound phone calls, the hackathon team must connect Pipecat to a telephony provider or media gateway and publish the resulting session events to the dashboard.

The official repository page is a useful maturity signal without pretending to predict stability: it reported BSD-2-Clause licensing, 406 stars, 67 forks, 553 commits, and a repository creation date of June 21, 2025 when fetched. [4] The license is permissive and the source-owned model is suitable for rapid visual customization.

**Decision**: choose Pipecat Voice UI Kit if the agent pipeline is already Pipecat or if the team wants a broad set of operational controls and headless pieces. Do not choose it solely because SmallWebRTC sounds like phone infrastructure; the telephone media path is still a backend integration.

### 3. ElevenLabs UI: richest audio and voice surface catalog

ElevenLabs UI is the most directly aligned with the visual component request. Its official docs enumerate Audio Player, Bar Visualizer, Conversation, Conversation Bar, Live Waveform, Matrix, Message, Mic Selector, Orb, Response, Scrub Bar, Shimmering Text, Speech Input, Transcript Viewer, Voice Button, Voice Picker, and Waveform. [18] This is a notably strong set for an agent home screen: an orb can represent state, a waveform can show current activity, a transcript can show the conversation, and the voice picker and mic selector can serve setup or testing flows.

The installation model is also appropriate for a shadcn-like workflow. ElevenLabs describes the library as a custom registry built on shadcn/ui, and its CLI adds source components to the project. The docs show commands such as `pnpm dlx @elevenlabs/cli@latest components add orb`. [18] The official GitHub repository page identifies it as MIT licensed and, in the fetched snapshot, reported 2,390 stars, 170 forks, 66 commits, and a September 3, 2025 creation date. [20]

The main limitation is not the visual inventory; it is the boundary between UI and call infrastructure. The components can render an observer screen, but the dashboard must supply the live state and audio signal. A phone caller is not automatically represented by the browser's `MediaStream`; the backend has to translate call events and permitted media or level data into the props or state consumed by the visual components. If the team is already using ElevenLabs for the agent, this is a natural presentation layer. If the agent runs on another provider, the team should test whether the component APIs are sufficiently generic before committing the whole design system to them.

**Decision**: choose ElevenLabs UI when the team values a polished audio-first visual language and is prepared to build the session and telephony adapter separately. It is the best catalog for composing a striking call screen, but not the best standalone answer to inbound phone routing or observer data.

## Focused and Near-Miss Options

### orb-ui: excellent companion, not a complete library

orb-ui is a focused React library for making a realtime voice surface feel alive. Its official site describes animated voice orbs, audio-reactive feedback, clear session states, expressive themes, and provider adapters. The supported paths include Vapi, ElevenLabs, LiveKit, Pipecat, OpenAI Realtime, and Gemini Live, with controlled mode for custom stacks. [7] [10]

The component scope is intentionally narrow. It provides themes such as circle, bars, cloud, radial, and debug, and can represent connecting, listening, speaking, idle, and error states. [7] [10] It installs through `npm install orb-ui`, uses React, and in a Next.js App Router application must run in a client component because it uses hooks. [10] The fetched GitHub page reported MIT licensing, 61 stars, 5 forks, 140 commits, and a February 26, 2026 creation date. [10]

This makes orb-ui a strong add-on to LiveKit Agents UI or Pipecat Voice UI Kit. It is not a substitute for a transcript viewer, call queue, session timeline, audio player, or observer event model. Use it for the central call-state card, then use a broader library for the surrounding console.

### Deepgram UI: real components, clear provider coupling

Deepgram UI should not be dismissed as an SDK mislabeled as UI. Its official UI page identifies React components built on shadcn/ui and Tailwind v4, with a copy-in registry command and an npm alternative. [8] The documented inventory includes an animated orb, five-state voice button, conversation transcript, text input, microphone and speaker buttons, start button, connection status, microphone selector, response renderer, bar visualizer, and live waveform. [15]

The trade-off is coupling. The associated repository describes a voice-agent SDK, React components, and embeddable widget for the Deepgram Agent API, while the UI package is used with `@deepgram/react` and `AgentProvider`. [15] [15] The fetched repository page reported MIT licensing, 162 commits, and a March 12, 2026 creation date, but zero stars in that snapshot. [15] That is a reason to treat it as promising and provider-specific, not as the safest foundation for an arbitrary phone backend.

### assistant-ui: useful adapter-based voice controls

assistant-ui is a general TypeScript/React AI chat library with a real voice slice. Its voice documentation provides realtime connect, mute, status, disconnect, and an animated orb, and it accepts any `RealtimeVoiceAdapter`, including LiveKit and ElevenLabs examples. [19] [19] All subcomponents can be used independently, which makes it useful for embedding voice controls into an existing chat or case-management interface. [19]

Its official license file states MIT, and the fetched repository page reported 12,206 stars, 1,184 forks, and 5,502 commits. [22] [23] The limitation is scope: it is a general AI chat frontend with a voice control layer, not a complete phone receptionist observer console. It is a good composition choice if the clinic dashboard already needs rich chat, tool calls, persistence, and a small realtime voice panel.

### Vercel AI Elements: general AI registry with only a light voice signal

AI Elements is a shadcn-based custom registry with composable AI-native building blocks, AI SDK integration, streaming, status states, and type safety. Its installation command adds selected source components directly into the application codebase. [3] [3] The official material includes voice agents among supported experiences and shows a Voice prompt control in a chatbot example, but the retrieved inventory does not show the dedicated orb, waveform, transcript, call-control, and audio-player breadth found in ElevenLabs, LiveKit, or Pipecat. [3] [3] [3]

The fetched repository page showed a license file, 2,437 stars, 278 forks, and 516 commits, but the retrieved primary excerpt did not state the license type. [9] [9] Treat it as a strong general AI composition layer, not as a turnkey voice-agent UI choice.

### Hume: provider platform and SDK surface, not a reusable collection

Hume is important to investigate because EVI is a real voice-agent product, but the official docs describe APIs and SDK quickstarts for TypeScript, Python, .NET, and the CLI rather than a reusable multi-component UI library. [11] [11] The same documentation describes integrations with Vercel AI SDK, LiveKit, Pipecat, Vapi, Twilio, and Agora, and presents Hume as a voice or text-to-speech provider inside those systems. [11]

That makes Hume relevant as a backend or provider integration, not as the answer to the requested library search. The separate embed renderer is better classified as an example or focused widget implementation than as a broad component collection. For this project, use Hume only if its empathic voice behavior is a deliberate product requirement, and source the observer controls from a separate UI library.

## Telephone Receptionist Architecture

The browser microphone is not the telephone call. The correct architecture has four layers:

| Layer | Responsibility | Dashboard output |
|---|---|---|
| Telephony ingress | Phone number, carrier or SIP provider, inbound trunk, caller identity, answer and hangup events | Ringing, connected, ended, caller metadata |
| Agent media/runtime | Bridge caller audio to the agent, run STT/LLM/TTS, emit turn and tool events | Listening, speaking, thinking, tool call, escalation, latency state |
| Event and media gateway | Authenticate and normalize events for the browser; publish transcript deltas and permitted audio or level data | Realtime websocket or WebRTC observer feed |
| Observer UI | Render session controls, transcript, waveform/orb, call metadata, alerts, and post-call timeline | Clinic dashboard and supervisor controls |

LiveKit's official inbound-call documentation says to accept inbound calls and route them to LiveKit rooms, configure inbound trunks and dispatch rules, and add callers as SIP participants. [6] Its observability documentation says LiveKit Cloud can provide transcripts, traces, logs, and actual audio recordings in a unified timeline for agent sessions. [13] Those facts support a clean implementation pattern: the agent and telephony backend publish the event stream, while the observer UI subscribes to a dashboard-specific projection.

For a hackathon, expose a small typed event contract rather than passing raw provider objects into components:

```ts
type CallEvent =
  | { type: "ringing"; callId: string; callerLabel?: string }
  | { type: "connected"; callId: string; startedAt: string }
  | { type: "agent_state"; state: "listening" | "speaking" | "thinking" }
  | { type: "transcript"; speaker: "caller" | "agent"; text: string; final: boolean }
  | { type: "audio_level"; source: "caller" | "agent"; level: number }
  | { type: "ended"; callId: string; reason?: string };
```

The UI can map `agent_state` and `audio_level` into LiveKit visualizers, Pipecat visualizers, ElevenLabs waveforms, orb-ui, or assistant-ui's orb. The transcript component should consume normalized transcript turns, not assume that browser speech recognition produced them. The observer should also distinguish live audio monitoring from a transcript-only mode, because recording or relaying patient audio has privacy, consent, retention, and access-control implications that belong in the backend and product policy.

A practical live observer layout is: a top call-status bar; a central orb or waveform; a two-sided transcript; a right rail for caller metadata, appointment intent, tool calls, and escalation; and a bottom control strip for mute-monitor, stop-agent, transfer, and hangup where permissions allow. The library supplies the visual primitives, but the event gateway supplies truth about the telephone session.

## Recommended Hackathon Build Plan

### Choice 1: LiveKit Agents UI plus LiveKit Telephony

Use this when the team wants the most integrated path. Start with LiveKit inbound SIP routing, create the agent room, add Agents UI media and session controls, then add the transcript and visualizer components. LiveKit's registry installation keeps the source in the app, and the telephony docs already model inbound calls as room participants. [17] [6]

The first demo milestone should be a real inbound call that appears as `ringing`, becomes `connected`, renders caller and agent transcript turns, and exposes a supervisor view. The second milestone adds permitted audio monitoring and call actions. This path minimizes the risk that the frontend prototype works only with a browser microphone.

### Choice 2: Pipecat Voice UI Kit plus a telephony/media gateway

Use this when the team has chosen Pipecat for the voice pipeline or wants maximum ownership of the UI source. Start with the Console template or compose `PipecatAppBase`, `VoiceVisualizer`, `UserAudioControl`, and `ConnectButton`. Add the transcript, session, DTMF, and function-call pieces as the dashboard grows. [16]

Treat SmallWebRTC as the browser-side transport for development or web sessions. Separately integrate the phone provider or SIP/media gateway, then publish normalized call events to the same UI state store. This gives the team a reusable dashboard but does not imply that SmallWebRTC supplies the phone number or carrier integration.

### Choice 3: ElevenLabs UI plus a custom backend adapter

Use this when the product demo needs the strongest audio-first polish or the agent already uses ElevenLabs. Add Orb, Live Waveform, Bar Visualizer, Audio Player, Voice Button, Mic Selector, Voice Picker, Transcript Viewer, and Conversation selectively rather than installing an entire visual system. [18]

Do not wire the orb to `navigator.mediaDevices` and call the telephone problem solved. The backend must translate inbound-call and agent events into the component state, and it must decide whether the observer receives raw audio, level-only data, or transcript events. If time is tight, build transcript and state monitoring first and make audio monitoring an explicitly permissioned second milestone.

**Companion choice**: If the team already has a transport layer and wants a single polished hero control, add orb-ui. If the surrounding application is a case-management chat interface, add assistant-ui's adapter-based voice controls. Neither should replace the backend call-event contract.

## Synthesis

The candidates differ along four important dimensions: breadth, transport coupling, source ownership, and observer readiness.

| Dimension | LiveKit Agents UI | Pipecat Voice UI Kit | ElevenLabs UI | orb-ui | assistant-ui |
|---|---|---|---|---|---|
| Breadth | Full agent UI categories: controls, visualizers, transcript [17] | Broad operational inventory plus templates [16] [16] | Broad audio and voice catalog [18] | Focused orb and state layer [10] | Voice control layer inside general AI chat [19] |
| Transport relationship | Strongly aligned with LiveKit realtime and SIP rooms [17] [6] | Pipecat-oriented; SmallWebRTC is one transport among several [16] | UI registry; backend adapter remains necessary [18] | Adapters for many providers [10] | Adapter abstraction for providers such as LiveKit and ElevenLabs [19] |
| Source ownership | shadcn source copied into app [17] | npm package plus headless components and templates [16] | CLI-added source components [18] | npm package with adapter model [10] | React components usable independently [19] |
| License evidence | Apache-2.0 repository [21] | BSD-2-Clause repository [4] | MIT repository [20] | MIT repository [10] | MIT license file [22] |
| Telephone suitability | Highest, because SIP ingress and rooms are first-class [6] | Depends on a separate phone/media integration | Depends on a separate phone/media integration | Visual companion only | Visual/chat companion only |

The non-obvious tension is that the most beautiful UI catalog and the best telephone architecture are not the same thing. ElevenLabs UI has the strongest visible audio inventory, while LiveKit has the clearest official path from phone ingress to realtime rooms. Pipecat offers the broadest source-owned operational toolkit, but SmallWebRTC should not be confused with carrier telephony. orb-ui is the most provider-flexible visual layer, but its narrow scope means it cannot carry the observer console alone.

Therefore the architecture should be selected before the component styling. For a clinic receptionist hackathon, the recommended sequence is: choose the telephony and agent runtime, normalize backend call events, prove a real inbound phone call, then compose the UI library around that event contract. The ranking is LiveKit Agents UI first, Pipecat Voice UI Kit second when Pipecat is the runtime, and ElevenLabs UI third for an audio-first presentation layer. Add orb-ui or assistant-ui only where their focused strengths solve a specific screen problem.

## References

1. *Hume AI · GitHub*. https://github.com/humeai
2. *GitHub - HumeAI/empathic-voice-embed-renderer: Renderer code for the marketing site voice widget · GitHub*. https://github.com/HumeAI/empathic-voice-embed-renderer
3. *AI Elements*. https://elements.ai-sdk.dev/
4. *GitHub - pipecat-ai/voice-ui-kit: Components, hooks and template apps for building React voice AI applications quickly. Designed to support and accelerate Pipecat AI development. · GitHub*. https://github.com/pipecat-ai/voice-ui-kit
5. *LiveKit Phone Numbers | Connect voice agents to phone lines | LiveKit*. https://livekit.com/products/livekit-phone-numbers
6. *Accepting calls overview*. https://docs.livekit.io/telephony/accepting-calls/
7. *orb-ui: React Voice Agent UI Components*. https://orb-ui.com/
8. *Deepgram UI — Voice Agent Components for React*. https://ui.deepgram.com/
9. *GitHub - vercel/ai-elements: AI Elements is a component library and custom registry built on top of shadcn/ui to help you build AI-native applications faster. · GitHub*. https://github.com/vercel/ai-elements
10. *GitHub - alexanderqchen/orb-ui: React voice AI component library with adapters for Vapi, ElevenLabs, LiveKit, Pipecat, OpenAI Realtime, and Gemini Live. · GitHub*. https://github.com/alexanderqchen/orb-ui
11. *hume.ai*. https://www.hume.ai/docs
12. *GitHub - pipecat-ai/pipecat: Open Source framework for voice agents, multimodal apps, and realtime AI. Maintained by Daily and the community. · GitHub*. https://github.com/pipecat-ai/pipecat
13. *Agent insights in LiveKit Cloud*. https://docs.livekit.io/agents/observability
14. *Voice Agent UI Components for React*. https://orb-ui.com/docs/guides/voice-agent-ui
15. *GitHub - deepgram/agent: Voice agent SDK, React components, and embeddable widget for the Deepgram Agent API · GitHub*. https://github.com/deepgram/agent
16. *Quickstart - Voice UI Kit*. https://voiceuikit.pipecat.ai/
17. *Agents UI components*. https://docs.livekit.io/frontends/components/agents-ui
18. *ElevenLabs UI | ElevenLabs UI*. https://ui.elevenlabs.io/docs
19. *Voice*. https://www.assistant-ui.com/docs/ui/voice
20. *GitHub - elevenlabs/ui: ElevenLabs UI is a component library and custom registry built on top of shadcn/ui to help you build multimodal agents faster. · GitHub*. https://github.com/elevenlabs/ui
21. *GitHub - livekit/components-js: Official open source React components and examples for building with LiveKit. · GitHub*. https://github.com/livekit/components-js
22. *assistant-ui/LICENSE at main · assistant-ui/assistant-ui · GitHub*. https://github.com/assistant-ui/assistant-ui/blob/main/LICENSE
23. *GitHub - assistant-ui/assistant-ui: Typescript/React Library for AI Chat 💬🚀 · GitHub*. https://github.com/assistant-ui/assistant-ui
