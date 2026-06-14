<script>
  import { onMount } from 'svelte'

  let page = 'home'
  let nick = localStorage.getItem('nick') || ''
  let rooms = []
  let games = []
  let creating = false
  let newRoomName = ''
  let selectedGame = ''

  // room state
  let currentRoom = null
  let players = []
  let host = null
  let messages = []
  let ws = null
  let inputText = ''
  let messagesEl

  async function loadRooms() {
    const r = await fetch('/rooms')
    rooms = await r.json()
  }

  async function loadGames() {
    const r = await fetch('/games')
    games = await r.json()
    if (games.length) selectedGame = games[0]
  }

  async function createRoom() {
    if (!nick.trim() || !newRoomName.trim()) return
    localStorage.setItem('nick', nick.trim())
    const r = await fetch(
      `/rooms?name=${encodeURIComponent(newRoomName)}&game=${selectedGame}&nick=${encodeURIComponent(nick.trim())}`,
      { method: 'POST' }
    )
    if (!r.ok) {
      const e = await r.json()
      alert(e.detail)
      return
    }
    const data = await r.json()
    enterRoom(data)
    creating = false
    newRoomName = ''
  }

  function joinRoom(room) {
    if (!nick.trim()) { alert('Enter nick first'); return }
    localStorage.setItem('nick', nick.trim())
    enterRoom(room)
  }

  function enterRoom(room) {
    currentRoom = room
    messages = []
    players = []
    host = room.host

    const proto = location.protocol === 'https:' ? 'wss' : 'ws'
    ws = new WebSocket(`${proto}://${location.host}/ws/${room.room_id || room.id}?nick=${encodeURIComponent(nick.trim())}`)

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.type === 'player_joined' || msg.type === 'player_left') {
        players = msg.players
        if (msg.host) host = msg.host
      }
      messages = [...messages, msg]
      setTimeout(() => messagesEl?.scrollTo(0, messagesEl.scrollHeight), 0)
    }

    ws.onclose = (e) => {
      messages = [...messages, { type: 'system', text: `Disconnected (${e.code})` }]
      setTimeout(() => { page = 'home'; loadRooms() }, 1500)
    }

    page = 'room'
  }

  function sendMessage() {
    if (!inputText.trim() || !ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(JSON.stringify({ type: 'message', data: inputText.trim() }))
    inputText = ''
  }

  function leaveRoom() {
    ws?.close()
  }

  onMount(() => { loadRooms(); loadGames() })
</script>

{#if page === 'home'}
  <div class="page home">
    <header>
      <h1>🎮 Play API</h1>
      <div class="nick-row">
        <input bind:value={nick} placeholder="Your nick" maxlength="20" />
      </div>
    </header>

    <main>
      <div class="section-header">
        <h2>Rooms</h2>
        <div class="actions">
          <button on:click={loadRooms} class="ghost">↻ Refresh</button>
          <button on:click={() => creating = !creating} class="primary">+ Create</button>
        </div>
      </div>

      {#if creating}
        <div class="create-form">
          <input bind:value={newRoomName} placeholder="Room name" maxlength="40" />
          <select bind:value={selectedGame}>
            {#each games as g}
              <option value={g}>{g}</option>
            {/each}
          </select>
          <button on:click={createRoom} class="primary">Create & Join</button>
          <button on:click={() => creating = false} class="ghost">Cancel</button>
        </div>
      {/if}

      <div class="room-list">
        {#each rooms as room (room.id)}
          <div class="room-card">
            <div class="room-meta">
              <span class="room-name">{room.name}</span>
              <span class="badge game">{room.game}</span>
              <span class="badge host">host: {room.host}</span>
            </div>
            <div class="room-footer">
              <span class="players-count">{room.players.length} player{room.players.length !== 1 ? 's' : ''}</span>
              {#if room.players.length > 0}
                <span class="player-names">{room.players.join(', ')}</span>
              {/if}
              <button on:click={() => joinRoom(room)} class="primary small">Join</button>
            </div>
          </div>
        {:else}
          <p class="empty">No rooms yet. Create one!</p>
        {/each}
      </div>
    </main>
  </div>

{:else}
  <div class="page room-page">
    <header>
      <div class="room-title">
        <h2>{currentRoom.name}</h2>
        <span class="badge game">{currentRoom.game}</span>
        {#if host === nick.trim()}<span class="badge you-host">YOU ARE HOST</span>{/if}
      </div>
      <button on:click={leaveRoom} class="ghost">Leave</button>
    </header>

    <div class="room-body">
      <aside class="sidebar">
        <h3>Players</h3>
        {#each players as p}
          <div class="player-row" class:you={p === nick.trim()}>
            {#if p === host}<span class="crown">👑</span>{/if}
            <span>{p}</span>
            {#if p === nick.trim()}<span class="you-label">(you)</span>{/if}
          </div>
        {:else}
          <p class="empty">Connecting...</p>
        {/each}
      </aside>

      <div class="chat">
        <div class="messages" bind:this={messagesEl}>
          {#each messages as msg}
            {#if msg.type === 'message'}
              <div class="msg" class:own={msg.from === nick.trim()}>
                <span class="from">{msg.from}:</span>
                <span class="text">{typeof msg.data === 'string' ? msg.data : JSON.stringify(msg.data)}</span>
              </div>
            {:else if msg.type === 'player_joined'}
              <div class="msg system">→ {msg.nick} joined</div>
            {:else if msg.type === 'player_left'}
              <div class="msg system">← {msg.nick} left</div>
            {:else if msg.type === 'system'}
              <div class="msg system">{msg.text}</div>
            {:else}
              <div class="msg system"><code>{JSON.stringify(msg)}</code></div>
            {/if}
          {/each}
        </div>

        <div class="input-row">
          <input
            bind:value={inputText}
            placeholder="Message…"
            on:keydown={(e) => e.key === 'Enter' && sendMessage()}
          />
          <button on:click={sendMessage} class="primary">Send</button>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  :global(*, *::before, *::after) { box-sizing: border-box; margin: 0; padding: 0; }
  :global(body) { font-family: system-ui, sans-serif; background: #0f0f13; color: #e2e2e2; height: 100vh; }
  :global(#app) { height: 100vh; display: flex; flex-direction: column; }

  .page { display: flex; flex-direction: column; height: 100vh; }

  header {
    padding: 16px 24px;
    background: #1a1a24;
    border-bottom: 1px solid #2a2a3a;
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
  }

  h1 { font-size: 1.4rem; color: #a78bfa; }
  h2 { font-size: 1.1rem; }
  h3 { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em; color: #888; margin-bottom: 8px; }

  .nick-row input { padding: 6px 10px; border-radius: 6px; border: 1px solid #3a3a4a; background: #0f0f13; color: #e2e2e2; font-size: 0.9rem; }

  main { padding: 24px; overflow-y: auto; flex: 1; }

  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
  .actions { display: flex; gap: 8px; }

  .create-form { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; padding: 16px; background: #1a1a24; border-radius: 8px; border: 1px solid #2a2a3a; }
  .create-form input, .create-form select { padding: 8px 10px; border-radius: 6px; border: 1px solid #3a3a4a; background: #0f0f13; color: #e2e2e2; font-size: 0.9rem; }

  .room-list { display: flex; flex-direction: column; gap: 10px; }

  .room-card { background: #1a1a24; border: 1px solid #2a2a3a; border-radius: 8px; padding: 14px 16px; display: flex; flex-direction: column; gap: 8px; }
  .room-meta { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .room-name { font-weight: 600; }
  .room-footer { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
  .players-count { font-size: 0.8rem; color: #888; }
  .player-names { font-size: 0.8rem; color: #aaa; flex: 1; }

  .badge { font-size: 0.7rem; padding: 2px 8px; border-radius: 99px; font-weight: 600; }
  .badge.game { background: #2d1f6e; color: #a78bfa; }
  .badge.host { background: #1a2a1a; color: #86efac; }
  .badge.you-host { background: #4a2700; color: #fbbf24; }

  .empty { color: #555; font-size: 0.9rem; padding: 16px 0; }

  /* Room page */
  .room-title { display: flex; align-items: center; gap: 8px; flex: 1; flex-wrap: wrap; }

  .room-body { display: flex; flex: 1; overflow: hidden; }

  .sidebar { width: 180px; min-width: 140px; padding: 16px; border-right: 1px solid #2a2a3a; background: #1a1a24; overflow-y: auto; }
  .player-row { display: flex; align-items: center; gap: 6px; padding: 6px 0; font-size: 0.9rem; border-bottom: 1px solid #222; }
  .player-row.you { color: #a78bfa; }
  .you-label { font-size: 0.75rem; color: #888; }
  .crown { font-size: 0.9rem; }

  .chat { display: flex; flex-direction: column; flex: 1; overflow: hidden; }

  .messages { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 6px; }

  .msg { padding: 6px 10px; border-radius: 6px; font-size: 0.9rem; max-width: 80%; }
  .msg.system { color: #666; font-style: italic; font-size: 0.8rem; align-self: center; background: none; padding: 2px 0; }
  .msg:not(.system):not(.own) { background: #1a1a24; align-self: flex-start; }
  .msg.own { background: #2d1f6e; align-self: flex-end; }
  .msg .from { font-weight: 600; color: #a78bfa; margin-right: 6px; }
  .msg code { font-size: 0.75rem; color: #888; }

  .input-row { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid #2a2a3a; background: #1a1a24; }
  .input-row input { flex: 1; padding: 8px 12px; border-radius: 6px; border: 1px solid #3a3a4a; background: #0f0f13; color: #e2e2e2; font-size: 0.9rem; }

  button { padding: 8px 16px; border-radius: 6px; border: none; cursor: pointer; font-size: 0.9rem; font-weight: 500; transition: opacity 0.1s; }
  button:hover { opacity: 0.85; }
  button.primary { background: #7c3aed; color: #fff; }
  button.ghost { background: #2a2a3a; color: #ccc; }
  button.small { padding: 5px 12px; font-size: 0.8rem; }
</style>
