// ─────────────────────────────────────────────────────────────
// NovelCast Studio — Client-Side Application Logic (ES Module)
// ─────────────────────────────────────────────────────────────

class NovelCastStudio {
  constructor() {
    this.state = {
      activeProject: 'vol2',
      activeChapter: null,
      chaptersList: [],
      segments: [],
      voices: {},
      availableSamples: [],
      engineMode: 'remote', // 'remote' or 'local'
      remoteUrl: 'http://192.168.0.180:9880/synthesize',
      activeLineIndex: -1,
      continuousPlay: true,
      isPlaying: false,
    };

    this.audioPlayer = document.getElementById('globalAudioPlayer');
    this.initElements();
    this.bindEvents();
    this.initApp();
  }

  initElements() {
    // Top Nav & Mode Switcher
    this.projectSelect = document.getElementById('projectSelect');
    this.btnModeRemote = document.getElementById('btnModeRemote');
    this.btnModeLocal = document.getElementById('btnModeLocal');
    this.engineStatusBadge = document.getElementById('engineStatusBadge');
    this.statusText = document.getElementById('statusText');
    this.navTabs = document.querySelectorAll('.nav-tab');
    this.tabPanels = document.querySelectorAll('.tab-panel');

    // Tab 1: Script Studio
    this.chapterSelect = document.getElementById('chapterSelect');
    this.statSegments = document.getElementById('statSegments');
    this.statCached = document.getElementById('statCached');
    this.scriptSearch = document.getElementById('scriptSearch');
    this.btnSaveScript = document.getElementById('btnSaveScript');
    this.btnStitchActiveChapter = document.getElementById('btnStitchActiveChapter');
    this.scriptRowsContainer = document.getElementById('scriptRowsContainer');

    // Tab 2: Voice Casting
    this.castCardsGrid = document.getElementById('castCardsGrid');
    this.btnRefreshVoices = document.getElementById('btnRefreshVoices');

    // Tab 3: M4B Packaging
    this.txtBookTitle = document.getElementById('txtBookTitle');
    this.txtAuthor = document.getElementById('txtAuthor');
    this.txtCoverPath = document.getElementById('txtCoverPath');
    this.coverPreviewImg = document.getElementById('coverPreviewImg');
    this.txtBitrate = document.getElementById('txtBitrate');
    this.sliderSpeakerChange = document.getElementById('sliderSpeakerChange');
    this.valSpeakerChange = document.getElementById('valSpeakerChange');
    this.sliderSameSpeaker = document.getElementById('sliderSameSpeaker');
    this.valSameSpeaker = document.getElementById('valSameSpeaker');
    this.btnStitchAllChapters = document.getElementById('btnStitchAllChapters');
    this.btnPackageMasterM4B = document.getElementById('btnPackageMasterM4B');
    this.chapterChecklistContainer = document.getElementById('chapterChecklistContainer');
    this.exportResultCard = document.getElementById('exportResultCard');
    this.btnDownloadM4B = document.getElementById('btnDownloadM4B');
    this.exportTitle = document.getElementById('exportTitle');
    this.exportMeta = document.getElementById('exportMeta');

    // Tab 4: Dubbing
    this.btnStartDubbing = document.getElementById('btnStartDubbing');
    this.dubProgressBox = document.getElementById('dubProgressBox');
    this.dubLogs = document.getElementById('dubLogs');

    // Bottom Player
    this.btnPlayPause = document.getElementById('btnPlayPause');
    this.btnPrevLine = document.getElementById('btnPrevLine');
    this.btnNextLine = document.getElementById('btnNextLine');
    this.playerSpeaker = document.getElementById('playerSpeaker');
    this.playerLineText = document.getElementById('playerLineText');
    this.playerCurrentTime = document.getElementById('playerCurrentTime');
    this.playerDuration = document.getElementById('playerDuration');
    this.playerSeek = document.getElementById('playerSeek');
    this.chkContinuousPlay = document.getElementById('chkContinuousPlay');
    this.playbackRate = document.getElementById('playbackRate');
  }

  bindEvents() {
    // Navigation Tabs
    this.navTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const targetTab = tab.getAttribute('data-tab');
        this.switchTab(targetTab);
      });
    });

    // Project Switcher
    this.projectSelect.addEventListener('change', (e) => {
      this.state.activeProject = e.target.value;
      this.loadProject();
    });

    // Engine Mode Toggle (Remote vs Local)
    this.btnModeRemote.addEventListener('click', () => this.setEngineMode('remote'));
    this.btnModeLocal.addEventListener('click', () => this.setEngineMode('local'));

    // Chapter Select
    this.chapterSelect.addEventListener('change', (e) => {
      this.state.activeChapter = e.target.value;
      this.loadChapterScript(this.state.activeChapter);
    });

    // Search Filter
    this.scriptSearch.addEventListener('input', (e) => {
      this.filterScriptRows(e.target.value);
    });

    // Save Edits
    this.btnSaveScript.addEventListener('click', () => this.saveScriptEdits());

    // Single Chapter Stitch
    this.btnStitchActiveChapter.addEventListener('click', () => this.stitchActiveChapter());

    // Voice Bank Refresh
    this.btnRefreshVoices.addEventListener('click', () => this.loadVoiceBank());

    // Pause Timing Sliders
    this.sliderSpeakerChange.addEventListener('input', (e) => {
      this.valSpeakerChange.textContent = e.target.value;
    });
    this.sliderSameSpeaker.addEventListener('input', (e) => {
      this.valSameSpeaker.textContent = e.target.value;
    });

    // Packaging Actions
    this.btnStitchAllChapters.addEventListener('click', () => this.stitchAllChapters());
    this.btnPackageMasterM4B.addEventListener('click', () => this.packageMasterM4B());

    // Bottom Player Controls
    this.btnPlayPause.addEventListener('click', () => this.togglePlayPause());
    this.btnPrevLine.addEventListener('click', () => this.playPreviousLine());
    this.btnNextLine.addEventListener('click', () => this.playNextLine());
    this.chkContinuousPlay.addEventListener('change', (e) => {
      this.state.continuousPlay = e.target.checked;
    });
    this.playbackRate.addEventListener('change', (e) => {
      this.audioPlayer.playbackRate = parseFloat(e.target.value);
    });

    this.audioPlayer.addEventListener('timeupdate', () => this.updatePlayerProgress());
    this.audioPlayer.addEventListener('ended', () => this.onLineAudioEnded());
    this.playerSeek.addEventListener('input', (e) => {
      if (this.audioPlayer.duration) {
        this.audioPlayer.currentTime = (e.target.value / 100) * this.audioPlayer.duration;
      }
    });

    // Dubbing Trigger
    this.btnStartDubbing.addEventListener('click', () => this.startDubbingDemo());
  }

  async initApp() {
    await this.checkEngineHealth();
    await this.loadVoiceBank();
    await this.loadProject();

    // Poll engine health every 15s
    setInterval(() => this.checkEngineHealth(), 15000);
  }

  // ─────────────────────────────────────────────────────────────
  // Tab Switching
  // ─────────────────────────────────────────────────────────────
  switchTab(tabKey) {
    this.navTabs.forEach(t => t.classList.toggle('active', t.getAttribute('data-tab') === tabKey));
    
    const panelMap = {
      scriptStudio: 'tabScriptStudio',
      voiceCasting: 'tabVoiceCasting',
      packagingStudio: 'tabPackagingStudio',
      dubbingStudio: 'tabDubbingStudio'
    };

    this.tabPanels.forEach(p => {
      p.classList.toggle('active', p.id === panelMap[tabKey]);
    });

    if (tabKey === 'packagingStudio') {
      this.renderChapterChecklist();
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Engine Mode & Health Check
  // ─────────────────────────────────────────────────────────────
  setEngineMode(mode) {
    this.state.engineMode = mode;
    this.btnModeRemote.classList.toggle('active', mode === 'remote');
    this.btnModeLocal.classList.toggle('active', mode === 'local');
    this.checkEngineHealth();
  }

  async checkEngineHealth() {
    try {
      const resp = await fetch(`/api/engine/status?remote_url=${encodeURIComponent(this.state.remoteUrl)}`);
      const data = await resp.json();

      if (this.state.engineMode === 'remote') {
        if (data.remote && data.remote.online) {
          this.engineStatusBadge.className = 'status-pill online';
          this.statusText.textContent = `Remote GPU (${data.remote.latency_ms}ms)`;
        } else {
          this.engineStatusBadge.className = 'status-pill offline';
          this.statusText.textContent = 'Remote GPU Offline';
        }
      } else {
        this.engineStatusBadge.className = 'status-pill online';
        this.statusText.textContent = `Local (${data.local.device})`;
      }
    } catch (e) {
      this.engineStatusBadge.className = 'status-pill offline';
      this.statusText.textContent = 'Engine Check Failed';
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Project & Chapter Loading
  // ─────────────────────────────────────────────────────────────
  async loadProject() {
    this.chapterSelect.innerHTML = '<option>Loading chapters...</option>';
    try {
      const resp = await fetch(`/api/scripts/${this.state.activeProject}`);
      this.state.chaptersList = await resp.json();

      this.chapterSelect.innerHTML = '';
      if (!this.state.chaptersList.length) {
        this.chapterSelect.innerHTML = '<option>No chapters found</option>';
        this.scriptRowsContainer.innerHTML = '<div class="loading-state"><p>No chapters in this project.</p></div>';
        return;
      }

      this.state.chaptersList.forEach((ch, idx) => {
        const opt = document.createElement('option');
        opt.value = ch.file;
        opt.textContent = `${idx + 1}. ${ch.title} (${ch.cached_segments}/${ch.total_segments} cached)`;
        this.chapterSelect.appendChild(opt);
      });

      this.state.activeChapter = this.state.chaptersList[0].file;
      await this.loadChapterScript(this.state.activeChapter);
      this.updatePackagingMetadata();
    } catch (e) {
      console.error('Failed to load project chapters:', e);
    }
  }

  async loadChapterScript(chapterId) {
    this.scriptRowsContainer.innerHTML = `
      <div class="loading-state">
        <div class="spinner"></div>
        <p>Loading Chapter Script...</p>
      </div>
    `;

    try {
      const resp = await fetch(`/api/scripts/${this.state.activeProject}/${encodeURIComponent(chapterId)}`);
      const data = await resp.json();
      this.state.segments = data.segments || [];

      // Update Chapter Stats
      const total = this.state.segments.length;
      const cached = this.state.segments.filter(s => s.is_cached).length;
      const pct = total ? Math.round((cached / total) * 100) : 0;

      this.statSegments.textContent = `${total} lines`;
      this.statCached.textContent = `${pct}% cached`;

      this.renderScriptTable(this.state.segments);
    } catch (e) {
      this.scriptRowsContainer.innerHTML = `<div class="loading-state"><p class="text-rose">Error loading script.</p></div>`;
    }
  }

  renderScriptTable(segments) {
    this.scriptRowsContainer.innerHTML = '';
    if (!segments.length) {
      this.scriptRowsContainer.innerHTML = '<div class="loading-state"><p>Script is empty.</p></div>';
      return;
    }

    segments.forEach((seg, idx) => {
      const row = document.createElement('div');
      row.className = 'script-row';
      row.id = `segRow_${idx}`;

      const spkLower = (seg.speaker || 'narrador').toLowerCase();
      const speakerClass = `speaker-${spkLower}`;

      row.innerHTML = `
        <div class="col-num">${seg.id}</div>
        <div class="col-speaker">
          <select class="studio-select speaker-dropdown" data-idx="${idx}">
            ${this.getSpeakerOptions(seg.speaker)}
          </select>
        </div>
        <div class="col-text">
          <input type="text" class="line-text-input" value="${this.escapeHtml(seg.text)}" data-idx="${idx}">
        </div>
        <div class="col-instruct">
          <select class="studio-select instruct-dropdown" data-idx="${idx}">
            ${this.getInstructOptions(seg.instruct)}
          </select>
        </div>
        <div class="col-status">
          <span class="cache-badge ${seg.is_cached ? 'cached' : 'uncached'}" id="cacheBadge_${idx}">
            ${seg.is_cached ? '✓ Cached' : '⚡ Missing'}
          </span>
        </div>
        <div class="col-actions line-actions">
          <button class="btn-icon btn-play-line" title="Audition Line" data-idx="${idx}">
            ▶
          </button>
          <button class="btn-icon btn-reroll-line" title="Re-roll / Synthesize Line" data-idx="${idx}">
            ⚡
          </button>
        </div>
      `;

      // Event listeners for inline edits & audition
      const textInput = row.querySelector('.line-text-input');
      textInput.addEventListener('change', (e) => {
        this.state.segments[idx].text = e.target.value;
      });

      const spkSelect = row.querySelector('.speaker-dropdown');
      spkSelect.addEventListener('change', (e) => {
        this.state.segments[idx].speaker = e.target.value;
      });

      const instSelect = row.querySelector('.instruct-dropdown');
      instSelect.addEventListener('change', (e) => {
        this.state.segments[idx].instruct = e.target.value || null;
      });

      const btnPlay = row.querySelector('.btn-play-line');
      btnPlay.addEventListener('click', () => this.playLineByIndex(idx));

      const btnReroll = row.querySelector('.btn-reroll-line');
      btnReroll.addEventListener('click', () => this.rerollSingleSegment(idx));

      this.scriptRowsContainer.appendChild(row);
    });
  }

  getSpeakerOptions(currentSpeaker) {
    const defaultSpeakers = ['Narrador', 'Subaru', 'Emilia', 'Roswaal', 'Beatrice', 'Rem', 'Ram', 'Puck', 'Elsa', 'Felt', 'Reinhard'];
    let opts = '';
    defaultSpeakers.forEach(s => {
      const sel = (s.toLowerCase() === (currentSpeaker || '').toLowerCase()) ? 'selected' : '';
      opts += `<option value="${s}" ${sel}>${s}</option>`;
    });
    return opts;
  }

  getInstructOptions(currentInstruct) {
    const tonePresets = [
      { label: 'Normal / Default', val: '' },
      { label: 'High Pitch (Energetic)', val: 'female, young adult, high pitch' },
      { label: 'Moderate Male', val: 'male, teenager, moderate pitch' },
      { label: 'Deep Male', val: 'male, middle-aged, low pitch' },
      { label: 'Child / Cute', val: 'female, child, high pitch' },
      { label: 'Whisper / Soft', val: 'female, whisper, young adult' }
    ];

    let opts = '';
    tonePresets.forEach(t => {
      const sel = (t.val === (currentInstruct || '')) ? 'selected' : '';
      opts += `<option value="${t.val}" ${sel}>${t.label}</option>`;
    });
    return opts;
  }

  filterScriptRows(query) {
    const q = query.toLowerCase().trim();
    this.state.segments.forEach((seg, idx) => {
      const row = document.getElementById(`segRow_${idx}`);
      if (!row) return;
      const matches = seg.text.toLowerCase().includes(q) || seg.speaker.toLowerCase().includes(q);
      row.style.display = matches ? 'grid' : 'none';
    });
  }

  // ─────────────────────────────────────────────────────────────
  // Instant Line Audition & Re-roll
  // ─────────────────────────────────────────────────────────────
  async playLineByIndex(idx) {
    const seg = this.state.segments[idx];
    if (!seg) return;

    this.state.activeLineIndex = idx;
    this.highlightActiveRow(idx);

    this.playerSpeaker.textContent = seg.speaker;
    this.playerLineText.textContent = seg.text;

    if (seg.audio_url) {
      this.audioPlayer.src = seg.audio_url;
      this.audioPlayer.play();
      this.state.isPlaying = true;
      this.btnPlayPause.textContent = '⏸';
    } else {
      // Synthesize on the fly
      await this.rerollSingleSegment(idx, true);
    }
  }

  async rerollSingleSegment(idx, autoPlay = true) {
    const seg = this.state.segments[idx];
    const badge = document.getElementById(`cacheBadge_${idx}`);
    if (badge) {
      badge.className = 'cache-badge uncached';
      badge.textContent = '⚙ Generating...';
    }

    try {
      const payload = {
        project_id: this.state.activeProject,
        chapter_id: this.state.activeChapter,
        segment: seg,
        engine: 'omnivoice',
        mode: this.state.engineMode,
        remote_url: this.state.remoteUrl
      };

      const resp = await fetch('/api/segments/regenerate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const res = await resp.json();
      if (res.success && res.audio_url) {
        seg.is_cached = true;
        seg.audio_url = res.audio_url;

        if (badge) {
          badge.className = 'cache-badge cached';
          badge.textContent = '✓ Cached';
        }

        if (autoPlay) {
          this.audioPlayer.src = res.audio_url;
          this.audioPlayer.play();
          this.state.isPlaying = true;
          this.btnPlayPause.textContent = '⏸';
        }
      }
    } catch (e) {
      if (badge) {
        badge.className = 'cache-badge uncached';
        badge.textContent = '✗ Failed';
      }
    }
  }

  highlightActiveRow(idx) {
    document.querySelectorAll('.script-row').forEach(r => r.classList.remove('active-playing'));
    const activeRow = document.getElementById(`segRow_${idx}`);
    if (activeRow) {
      activeRow.classList.add('active-playing');
      activeRow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  onLineAudioEnded() {
    if (this.state.continuousPlay && this.state.activeLineIndex < this.state.segments.length - 1) {
      this.playLineByIndex(this.state.activeLineIndex + 1);
    } else {
      this.state.isPlaying = false;
      this.btnPlayPause.textContent = '▶';
    }
  }

  togglePlayPause() {
    if (!this.audioPlayer.src) {
      if (this.state.segments.length) this.playLineByIndex(0);
      return;
    }

    if (this.audioPlayer.paused) {
      this.audioPlayer.play();
      this.state.isPlaying = true;
      this.btnPlayPause.textContent = '⏸';
    } else {
      this.audioPlayer.pause();
      this.state.isPlaying = false;
      this.btnPlayPause.textContent = '▶';
    }
  }

  playPreviousLine() {
    if (this.state.activeLineIndex > 0) {
      this.playLineByIndex(this.state.activeLineIndex - 1);
    }
  }

  playNextLine() {
    if (this.state.activeLineIndex < this.state.segments.length - 1) {
      this.playLineByIndex(this.state.activeLineIndex + 1);
    }
  }

  updatePlayerProgress() {
    if (this.audioPlayer.duration) {
      const pct = (this.audioPlayer.currentTime / this.audioPlayer.duration) * 100;
      this.playerSeek.value = pct || 0;
      this.playerCurrentTime.textContent = this.formatTime(this.audioPlayer.currentTime);
      this.playerDuration.textContent = this.formatTime(this.audioPlayer.duration);
    }
  }

  formatTime(secs) {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  }

  async saveScriptEdits() {
    try {
      const payload = {
        segments: this.state.segments
      };
      const resp = await fetch(`/api/scripts/${this.state.activeProject}/${encodeURIComponent(this.state.activeChapter)}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      if (data.success) {
        alert('Chapter script edits saved successfully!');
      }
    } catch (e) {
      alert('Failed to save script.');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Voice Casting Deck
  // ─────────────────────────────────────────────────────────────
  async loadVoiceBank() {
    try {
      const resp = await fetch('/api/voices');
      const data = await resp.json();
      this.state.voices = data.voices || {};
      this.state.availableSamples = data.available_samples || [];
      this.renderVoiceCastingDeck();
    } catch (e) {
      console.error('Failed to load voice bank:', e);
    }
  }

  renderVoiceCastingDeck() {
    this.castCardsGrid.innerHTML = '';
    const sampleOptions = this.state.availableSamples.map(s => `<option value="${s.name}">${s.name} (${s.size_kb} KB)</option>`).join('');

    const characters = ['Narrador', 'Subaru', 'Emilia', 'Roswaal', 'Beatrice', 'Rem', 'Ram', 'Puck'];
    characters.forEach(char => {
      const cLower = char.toLowerCase();
      const voiceConfig = this.state.voices[cLower] || {};
      const currentSample = voiceConfig.description || `${cLower}.wav`;

      const card = document.createElement('div');
      card.className = 'cast-card';
      card.innerHTML = `
        <div class="cast-card-top">
          <span class="cast-name">${char}</span>
          <span class="speaker-badge speaker-${cLower}">${char}</span>
        </div>
        <div class="form-group">
          <label>Assigned Reference Voice:</label>
          <select class="studio-select cast-sample-select" data-char="${char}">
            ${sampleOptions}
          </select>
        </div>
        <div class="cast-audio-row">
          <button class="btn-icon btn-audition-sample" title="Play Voice Sample" data-sample="${currentSample}">
            ▶
          </button>
          <span class="sample-name">${currentSample}</span>
        </div>
      `;

      const select = card.querySelector('.cast-sample-select');
      select.value = currentSample;
      select.addEventListener('change', async (e) => {
        await this.assignVoice(char, e.target.value);
      });

      const btnAudition = card.querySelector('.btn-audition-sample');
      btnAudition.addEventListener('click', () => {
        const sampleUrl = `/api/audio/sample?name=${encodeURIComponent(select.value)}`;
        this.audioPlayer.src = sampleUrl;
        this.audioPlayer.play();
        this.playerSpeaker.textContent = char;
        this.playerLineText.textContent = `Auditioning Voice: ${select.value}`;
        this.btnPlayPause.textContent = '⏸';
      });

      this.castCardsGrid.appendChild(card);
    });
  }

  async assignVoice(character, voiceFile) {
    try {
      await fetch('/api/voices/assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ character, voice_file: voiceFile })
      });
    } catch (e) {
      console.error('Failed to assign voice:', e);
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Packaging & M4B Compilation
  // ─────────────────────────────────────────────────────────────
  updatePackagingMetadata() {
    if (this.state.activeProject === 'vol2') {
      this.txtBookTitle.value = 'Re:Zero Volumen 2 (Novela Ligera)';
      this.txtAuthor.value = 'Tappei Nagatsuki';
      this.txtCoverPath.value = 'output/volume_2/cover_vol2.jpg';
      this.coverPreviewImg.src = '/api/audio/download?path=' + encodeURIComponent('output/volume_2/cover_vol2.jpg');
    } else if (this.state.activeProject === 'vol3') {
      this.txtBookTitle.value = 'Re:Zero Volumen 3 (Novela Ligera)';
      this.txtAuthor.value = 'Tappei Nagatsuki';
      this.txtCoverPath.value = 'output/volume_3/cover_vol3.jpg';
      this.coverPreviewImg.src = '/api/audio/download?path=' + encodeURIComponent('output/volume_3/cover_vol3.jpg');
    }
  }

  renderChapterChecklist() {
    this.chapterChecklistContainer.innerHTML = '';
    this.state.chaptersList.forEach((ch, idx) => {
      const item = document.createElement('div');
      item.className = 'check-item';
      item.innerHTML = `
        <div class="check-left">
          <span class="cache-badge ${ch.is_ready ? 'cached' : 'uncached'}">
            ${ch.is_ready ? '✓ Synthesized' : '⚠️ Missing Lines'}
          </span>
          <span class="check-title">${idx + 1}. ${ch.title}</span>
        </div>
        <div class="check-right">
          <span class="time-label">${ch.cached_segments}/${ch.total_segments}</span>
        </div>
      `;
      this.chapterChecklistContainer.appendChild(item);
    });
  }

  async stitchActiveChapter() {
    try {
      const payload = {
        project_id: this.state.activeProject,
        chapter_id: this.state.activeChapter,
        speaker_change_ms: parseInt(this.sliderSpeakerChange.value),
        same_speaker_ms: parseInt(this.sliderSameSpeaker.value)
      };
      this.btnStitchActiveChapter.textContent = '⚙ Stitching...';
      const resp = await fetch('/api/tasks/stitch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      this.btnStitchActiveChapter.textContent = '🎧 Stitch Chapter MP3';
      if (data.success) {
        alert('Chapter MP3 stitched successfully!');
      }
    } catch (e) {
      this.btnStitchActiveChapter.textContent = '🎧 Stitch Chapter MP3';
      alert('Stitching failed.');
    }
  }

  async stitchAllChapters() {
    this.btnStitchAllChapters.textContent = '⚙ Stitching All...';
    try {
      const payload = {
        project_id: this.state.activeProject,
        speaker_change_ms: parseInt(this.sliderSpeakerChange.value),
        same_speaker_ms: parseInt(this.sliderSameSpeaker.value)
      };
      const resp = await fetch('/api/tasks/stitch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      this.btnStitchAllChapters.textContent = '🎧 Stitch All Chapters';
      if (data.success) {
        alert(`Successfully stitched ${data.stitched_chapters.length} chapters!`);
      }
    } catch (e) {
      this.btnStitchAllChapters.textContent = '🎧 Stitch All Chapters';
      alert('Stitching failed.');
    }
  }

  async packageMasterM4B() {
    this.btnPackageMasterM4B.textContent = '⚙ Compiling M4B...';
    try {
      const payload = {
        project_id: this.state.activeProject,
        title: this.txtBookTitle.value,
        author: this.txtAuthor.value,
        cover_image: this.txtCoverPath.value,
        bitrate: this.txtBitrate.value
      };
      const resp = await fetch('/api/tasks/package', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      this.btnPackageMasterM4B.textContent = '📦 Compile Master M4B Audiobook';

      if (data.success) {
        this.exportResultCard.classList.remove('hidden');
        this.exportTitle.textContent = `${this.txtBookTitle.value} Ready!`;
        this.exportMeta.textContent = `Size: ${data.size_mb} MB • AAC ${this.txtBitrate.value}`;
        this.btnDownloadM4B.href = data.download_url;
      }
    } catch (e) {
      this.btnPackageMasterM4B.textContent = '📦 Compile Master M4B Audiobook';
      alert('M4B compilation failed.');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Dubbing Studio
  // ─────────────────────────────────────────────────────────────
  startDubbingDemo() {
    this.dubProgressBox.classList.remove('hidden');
    this.dubLogs.textContent = "▶ Step 1/5: Loading source audiobook...\n▶ Step 2/5: Transcribing & Translating chapters (EN -> ES)...\n▶ Step 3/5: Synthesizing voice-cloned Spanish dubbing with OmniVoice...\n\n[Active dubbing process running in terminal]";
  }

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#039;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
}

// Instantiate Studio on Page Load
window.addEventListener('DOMContentLoaded', () => {
  window.novelCastStudio = new NovelCastStudio();
});
