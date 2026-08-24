// ─────────────────────────────────────────────────────────────
// NovelCast Studio — Client-Side Application Logic (ES Module)
// ─────────────────────────────────────────────────────────────

class NovelCastStudio {
  constructor() {
    this.state = {
      activeProject: 'vol2',
      activeChapter: null,
      projectsList: [],
      chaptersList: [],
      segments: [],
      voices: {},
      availableSamples: [],
      engineMode: 'remote', // 'remote' or 'local'
      remoteUrl: 'http://192.168.0.180:9880/synthesize',
      activeLineIndex: -1,
      continuousPlay: true,
      isPlaying: false,
      playbackMode: 'script', // 'script' or 'sample'
      selectedNewProjectType: 'epub'
    };

    this.audioPlayer = document.getElementById('globalAudioPlayer');
    this.initElements();
    this.bindEvents();
    this.initApp();
  }

  initElements() {
    // Top Nav & Mode Switcher
    this.projectSelect = document.getElementById('projectSelect');
    this.btnOpenNewProjectModal = document.getElementById('btnOpenNewProjectModal');
    this.btnDeleteProject = document.getElementById('btnDeleteProject');
    this.btnRun1ClickPipeline = document.getElementById('btnRun1ClickPipeline');
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
    this.btnSynthesizeChapter = document.getElementById('btnSynthesizeChapter');
    this.btnStitchActiveChapter = document.getElementById('btnStitchActiveChapter');
    this.scriptRowsContainer = document.getElementById('scriptRowsContainer');

    // Tab 2: Voice Casting
    this.castCardsGrid = document.getElementById('castCardsGrid');
    this.btnRefreshVoices = document.getElementById('btnRefreshVoices');
    this.btnAutoDetectCharacters = document.getElementById('btnAutoDetectCharacters');
    this.btnSaveVoiceCasting = document.getElementById('btnSaveVoiceCasting');
    this.detectedCharBadge = document.getElementById('detectedCharBadge');

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
    this.btnSynthesizeAllChapters = document.getElementById('btnSynthesizeAllChapters');
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

    // New Project Modal Elements
    this.modalNewProject = document.getElementById('modalNewProject');
    this.btnCloseModal = document.getElementById('btnCloseModal');
    this.btnCancelModal = document.getElementById('btnCancelModal');
    this.modalProjName = document.getElementById('modalProjName');
    this.modalProjAuthor = document.getElementById('modalProjAuthor');
    this.modalFileInput = document.getElementById('modalFileInput');
    this.selectedFileName = document.getElementById('selectedFileName');
    this.modalLocalPath = document.getElementById('modalLocalPath');
    this.modalParsingFeedback = document.getElementById('modalParsingFeedback');
    this.btnCreateProjectSubmit = document.getElementById('btnCreateProjectSubmit');
    this.typeCards = document.querySelectorAll('.type-card');
    this.epubDropzone = document.getElementById('epubDropzone');
    this.epubUploadGroup = document.getElementById('epubUploadGroup');
    this.chkAutoRunPipeline = document.getElementById('chkAutoRunPipeline');

    // Real-Time Pipeline Progress Modal Elements
    this.modalPipelineProgress = document.getElementById('modalPipelineProgress');
    this.btnCloseProgressModal = document.getElementById('btnCloseProgressModal');
    this.btnDismissProgressModal = document.getElementById('btnDismissProgressModal');
    this.pipelineProgressBar = document.getElementById('pipelineProgressBar');
    this.pipelineProgressPct = document.getElementById('pipelineProgressPct');
    this.pipelineStepName = document.getElementById('pipelineStepName');
    this.pipelineProgressSubtitle = document.getElementById('pipelineProgressSubtitle');
    this.pipelineLogsContainer = document.getElementById('pipelineLogsContainer');
    this.logItemCount = document.getElementById('logItemCount');
    this.pipelineSuccessBanner = document.getElementById('pipelineSuccessBanner');
    this.btnPipelineDownloadM4B = document.getElementById('btnPipelineDownloadM4B');
    this.successTitle = document.getElementById('successTitle');
    this.successMeta = document.getElementById('successMeta');
    this.pipelineModalTitle = document.getElementById('pipelineModalTitle');
    this.pipelineModalSubtitle = document.getElementById('pipelineModalSubtitle');
    this.btnPausePipeline = document.getElementById('btnPausePipeline');
    this.btnStopPipeline = document.getElementById('btnStopPipeline');

    // Mobile Header Navigation Elements
    this.btnMobileMenuToggle = document.getElementById('btnMobileMenuToggle');
    this.headerCollapsibleMenu = document.getElementById('headerCollapsibleMenu');
    this.mobileMenuBackdrop = document.getElementById('mobileMenuBackdrop');

    this.activeJobPollTimer = null;
    this.currentJobId = null;
  }

  bindEvents() {
    // Navigation Tabs
    this.navTabs.forEach(tab => {
      tab.addEventListener('click', () => {
        const targetTab = tab.getAttribute('data-tab');
        this.switchTab(targetTab);
      });
    });

    // Project Switcher & Actions
    this.projectSelect.addEventListener('change', (e) => {
      this.state.activeProject = e.target.value;
      this.loadProject();
    });

    this.btnDeleteProject.addEventListener('click', () => this.deleteCurrentProject());

    // 1-Click Production from Header
    this.btnRun1ClickPipeline.addEventListener('click', () => {
      const curProj = this.state.projectsList.find(p => p.id === this.state.activeProject);
      const title = curProj ? curProj.name : this.txtBookTitle.value;
      const author = this.txtAuthor.value;
      this.launchFullPipeline(this.state.activeProject, title, author);
    });

    // New Project Modal Triggers
    this.btnOpenNewProjectModal.addEventListener('click', () => this.openNewProjectModal());
    this.btnCloseModal.addEventListener('click', () => this.closeNewProjectModal());
    this.btnCancelModal.addEventListener('click', () => this.closeNewProjectModal());

    // Progress Modal Close Triggers
    this.btnCloseProgressModal.addEventListener('click', () => this.closeProgressModal());
    this.btnDismissProgressModal.addEventListener('click', () => this.closeProgressModal());

    // Modal Project Type Switcher
    this.typeCards.forEach(card => {
      card.addEventListener('click', () => {
        this.typeCards.forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        this.state.selectedNewProjectType = card.getAttribute('data-type');
        this.epubUploadGroup.style.display = (this.state.selectedNewProjectType === 'blank') ? 'none' : 'flex';
      });
    });

    // File Dropzone Handlers
    this.modalFileInput.addEventListener('change', (e) => {
      if (e.target.files && e.target.files[0]) {
        this.selectedFileName.textContent = `Selected: ${e.target.files[0].name}`;
        if (!this.modalProjName.value) {
          const cleanName = e.target.files[0].name.replace(/\.[^/.]+$/, "").replace(/[-_]/g, ' ');
          this.modalProjName.value = cleanName;
        }
      }
    });

    // Submit New Project
    this.btnCreateProjectSubmit.addEventListener('click', () => this.submitCreateProject());

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

    // Batch Synthesis
    this.btnSynthesizeChapter.addEventListener('click', () => this.synthesizeActiveChapter());
    this.btnSynthesizeAllChapters.addEventListener('click', () => this.synthesizeAllChapters());

    // Single Chapter Stitch
    this.btnStitchActiveChapter.addEventListener('click', () => this.stitchActiveChapter());

    // Voice Bank Actions
    this.btnRefreshVoices.addEventListener('click', () => this.loadVoiceBank());
    this.btnAutoDetectCharacters.addEventListener('click', () => this.detectProjectCharacters());
    this.btnSaveVoiceCasting.addEventListener('click', () => this.saveBatchVoiceCasting());

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

    // Pipeline Modal Controls
    this.btnPausePipeline.addEventListener('click', () => this.togglePauseJob());
    this.btnStopPipeline.addEventListener('click', () => this.stopJob());

    // Mobile Hamburger Navigation
    this.btnMobileMenuToggle?.addEventListener('click', () => this.toggleMobileMenu());
    
    // Auto-close mobile menu on window resize to desktop or click outside
    window.addEventListener('resize', () => {
      if (window.innerWidth > 1150) {
        this.closeMobileMenu();
      }
    });

    document.addEventListener('click', (e) => {
      if (this.headerCollapsibleMenu?.classList.contains('is-open')) {
        if (!e.target.closest('.studio-header')) {
          this.closeMobileMenu();
        }
      }
    });
  }

  async initApp() {
    await this.checkEngineHealth();
    await this.loadVoiceBank();
    await this.loadProjectsList();

    // Poll engine health every 15s
    setInterval(() => this.checkEngineHealth(), 15000);
  }

  // ─────────────────────────────────────────────────────────────
  // Projects List & Project Loading
  // ─────────────────────────────────────────────────────────────
  async loadProjectsList(selectProjectId = null) {
    try {
      const resp = await fetch('/api/projects');
      this.state.projectsList = await resp.json();

      this.projectSelect.innerHTML = '';
      this.state.projectsList.forEach(p => {
        const opt = document.createElement('option');
        opt.value = p.id;
        opt.textContent = `${p.name} (${p.chapters_count} ch)`;
        this.projectSelect.appendChild(opt);
      });

      if (selectProjectId && this.state.projectsList.some(p => p.id === selectProjectId)) {
        this.state.activeProject = selectProjectId;
      } else if (!this.state.activeProject && this.state.projectsList.length) {
        this.state.activeProject = this.state.projectsList[0].id;
      }

      this.projectSelect.value = this.state.activeProject;
      await this.loadProject();
    } catch (e) {
      console.error('Failed to load projects list:', e);
    }
  }

  async loadProject() {
    this.chapterSelect.innerHTML = '<option>Loading chapters...</option>';
    try {
      const resp = await fetch(`/api/scripts/${this.state.activeProject}`);
      this.state.chaptersList = await resp.json();

      this.chapterSelect.innerHTML = '';
      if (!this.state.chaptersList.length) {
        this.chapterSelect.innerHTML = '<option>No chapters found</option>';
        this.scriptRowsContainer.innerHTML = '<div class="loading-state"><p>No chapters in this project.</p></div>';
        this.statSegments.textContent = '0 lines';
        this.statCached.textContent = '0% cached';
      } else {
        this.state.chaptersList.forEach((ch, idx) => {
          const opt = document.createElement('option');
          opt.value = ch.file;
          opt.textContent = `${idx + 1}. ${ch.title} (${ch.cached_segments}/${ch.total_segments} cached)`;
          this.chapterSelect.appendChild(opt);
        });

        this.state.activeChapter = this.state.chaptersList[0].file;
        await this.loadChapterScript(this.state.activeChapter);
      }

      // Synchronize all other studio decks with the selected project
      this.updatePackagingMetadata();
      this.renderChapterChecklist();
      await this.detectProjectCharacters();
    } catch (e) {
      console.error('Failed to load project chapters:', e);
    }
  }

  async deleteCurrentProject() {
    const curProj = this.state.projectsList.find(p => p.id === this.state.activeProject);
    const projName = curProj ? curProj.name : this.state.activeProject;

    if (!confirm(`Are you sure you want to remove project "${projName}" from your workspace?`)) {
      return;
    }

    try {
      const resp = await fetch(`/api/projects/${this.state.activeProject}`, {
        method: 'DELETE'
      });
      const data = await resp.json();
      if (data.success) {
        alert(`✓ Project "${projName}" has been removed from workspace.`);
        this.state.activeProject = null;
        await this.loadProjectsList();
      } else {
        alert(`Could not delete project: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error('Error deleting project:', e);
      alert('Failed to delete project.');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // New Project Modal Wizard
  // ─────────────────────────────────────────────────────────────
  openNewProjectModal() {
    this.modalNewProject.classList.remove('hidden');
    this.modalProjName.value = '';
    this.modalFileInput.value = '';
    this.selectedFileName.textContent = 'No file selected';
    this.modalLocalPath.value = '';
    this.modalParsingFeedback.classList.add('hidden');
    this.btnCreateProjectSubmit.disabled = false;
    this.btnCreateProjectSubmit.innerHTML = '<span>✨</span> Create & Ingest Project';
  }

  closeNewProjectModal() {
    this.modalNewProject.classList.add('hidden');
  }

  async submitCreateProject() {
    const name = this.modalProjName.value.trim();
    if (!name) {
      alert('Please enter a Project Title.');
      return;
    }

    const formData = new FormData();
    formData.append('name', name);
    formData.append('project_type', this.state.selectedNewProjectType);
    formData.append('author', this.modalProjAuthor.value.trim());

    if (this.modalFileInput.files && this.modalFileInput.files[0]) {
      formData.append('file', this.modalFileInput.files[0]);
    }
    if (this.modalLocalPath.value.trim()) {
      formData.append('local_path', this.modalLocalPath.value.trim());
    }

    this.modalParsingFeedback.classList.remove('hidden');
    this.btnCreateProjectSubmit.disabled = true;
    this.btnCreateProjectSubmit.innerHTML = '<span>⚙</span> Ingesting...';

    try {
      const resp = await fetch('/api/projects/create', {
        method: 'POST',
        body: formData
      });

      const res = await resp.json();
      if (res.success) {
        this.closeNewProjectModal();
        await this.loadProjectsList(res.project_id);

        if (this.chkAutoRunPipeline.checked && this.state.selectedNewProjectType === 'epub') {
          // Launch 1-Click End-to-End Production
          this.launchFullPipeline(res.project_id, name, this.modalProjAuthor.value.trim());
        } else {
          this.switchTab('scriptStudio');
        }
      } else {
        alert('Failed to create project.');
      }
    } catch (e) {
      alert('Error creating project.');
    } finally {
      this.modalParsingFeedback.classList.add('hidden');
      this.btnCreateProjectSubmit.disabled = false;
      this.btnCreateProjectSubmit.innerHTML = '<span>✨</span> Create & Ingest Project';
    }
  }

  // ─────────────────────────────────────────────────────────────
  // 1-Click End-to-End Pipeline & Real-Time Job Tracker
  // ─────────────────────────────────────────────────────────────
  async launchFullPipeline(projectId, bookTitle, authorName) {
    if (this.activeJobPollTimer) clearInterval(this.activeJobPollTimer);

    // Reset Progress Modal UI
    this.modalPipelineProgress.classList.remove('hidden');
    this.pipelineSuccessBanner.classList.add('hidden');
    this.pipelineProgressBar.style.width = '0%';
    this.pipelineProgressPct.textContent = '0%';
    this.pipelineStepName.textContent = 'Initializing Pipeline...';
    this.pipelineProgressSubtitle.textContent = 'Queuing audiobook production tasks...';
    this.pipelineLogsContainer.innerHTML = '<div class="log-line info">[System] Starting 1-Click Pipeline for ' + (bookTitle || projectId) + '...</div>';
    this.logItemCount.textContent = '1 message';

    this.pipelineModalTitle.textContent = `🚀 Producing: ${bookTitle || projectId}`;

    this.resetStepCards();
    this.btnPausePipeline.innerHTML = '<span>⏸</span> Pause';
    this.btnPausePipeline.disabled = false;
    this.btnStopPipeline.disabled = false;

    try {
      const payload = {
        project_id: projectId,
        title: bookTitle,
        author: authorName,
        engine: 'omnivoice',
        mode: this.state.engineMode,
        remote_url: this.state.remoteUrl,
        workers: 4,
        speaker_change_ms: parseInt(this.sliderSpeakerChange.value),
        same_speaker_ms: parseInt(this.sliderSameSpeaker.value),
        bitrate: this.txtBitrate.value
      };

      const resp = await fetch('/api/pipeline/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await resp.json();
      if (data.job_id) {
        this.currentJobId = data.job_id;
        this.pollJobStatus(data.job_id);
      }
    } catch (e) {
      this.pipelineStepName.textContent = '❌ Failed to start pipeline.';
      this.pipelineProgressSubtitle.textContent = String(e);
    }
  }

  async togglePauseJob() {
    if (!this.currentJobId) return;
    try {
      const resp = await fetch(`/api/jobs/${this.currentJobId}/pause`, { method: 'POST' });
      const data = await resp.json();
      if (data.success) {
        this.btnPausePipeline.innerHTML = data.paused ? '<span>▶</span> Resume' : '<span>⏸</span> Pause';
        if (data.paused) {
          this.pipelineProgressSubtitle.textContent = '⏸ Pipeline is paused. Click Resume to continue.';
        }
      }
    } catch (e) {
      console.error('Error toggling pause:', e);
    }
  }

  async stopJob() {
    if (!this.currentJobId) return;
    if (!confirm('Are you sure you want to stop the production pipeline? Already synthesized chunks will remain safely cached.')) {
      return;
    }

    try {
      this.btnStopPipeline.disabled = true;
      this.btnPausePipeline.disabled = true;
      this.pipelineProgressSubtitle.textContent = '🛑 Stopping production pipeline...';
      const resp = await fetch(`/api/jobs/${this.currentJobId}/cancel`, { method: 'POST' });
      const data = await resp.json();
      if (data.success) {
        this.pipelineProgressSubtitle.textContent = '🛑 Production stopped by user.';
      }
    } catch (e) {
      console.error('Error stopping job:', e);
    }
  }

  pollJobStatus(jobId) {
    if (this.activeJobPollTimer) {
      clearInterval(this.activeJobPollTimer);
    }

    this.activeJobPollTimer = setInterval(async () => {
      try {
        const resp = await fetch(`/api/jobs/${jobId}`);
        if (!resp.ok) return;
        const job = await resp.json();
        this.updatePipelineProgressUI(job);

        if (job.status === 'completed' || job.status === 'failed' || job.status === 'stopped') {
          clearInterval(this.activeJobPollTimer);
          this.activeJobPollTimer = null;
          // Refresh studio state
          await this.loadProject();
        }
      } catch (e) {
        console.error('Job poll error:', e);
      }
    }, 800);
  }

  updatePipelineProgressUI(job) {
    const pct = Math.min(Math.max(job.progress_pct || 0, 0), 100);
    this.pipelineProgressBar.style.width = `${pct}%`;
    this.pipelineProgressPct.textContent = `${Math.round(pct)}%`;
    this.pipelineStepName.textContent = `Step ${job.step}/4: ${job.step_name}`;

    if (job.status === 'paused') {
      this.pipelineProgressSubtitle.textContent = '⏸ Pipeline is paused. Click Resume to continue.';
      this.btnPausePipeline.innerHTML = '<span>▶</span> Resume';
    } else if (job.status === 'stopped') {
      this.pipelineProgressSubtitle.textContent = '🛑 Production stopped.';
      this.btnPausePipeline.disabled = true;
      this.btnStopPipeline.disabled = true;
    } else if (job.current_item && job.total_items) {
      this.pipelineProgressSubtitle.textContent = `Processing chunk ${job.current_item} of ${job.total_items} (${job.step_name})`;
    } else {
      this.pipelineProgressSubtitle.textContent = job.logs[job.logs.length - 1] || 'Processing...';
    }

    // Update Steps
    for (let s = 1; s <= 4; s++) {
      const card = document.getElementById(`stepCard${s}`);
      const tag = document.getElementById(`step${s}Status`);
      if (!card || !tag) continue;

      if (s < job.step) {
        card.className = 'step-card completed';
        tag.className = 'step-status-tag completed';
        tag.textContent = '✓ Done';
      } else if (s === job.step) {
        card.className = 'step-card active';
        tag.className = 'step-status-tag active';
        tag.textContent = job.status === 'completed' ? '✓ Done' : (job.status === 'paused' ? 'Paused' : (job.status === 'stopped' ? 'Stopped' : 'Active'));
      } else {
        card.className = 'step-card';
        tag.className = 'step-status-tag';
        tag.textContent = 'Pending';
      }
    }

    if (job.status === 'completed') {
      const card4 = document.getElementById('stepCard4');
      const tag4 = document.getElementById('step4Status');
      if (card4 && tag4) {
        card4.className = 'step-card completed';
        tag4.className = 'step-status-tag completed';
        tag4.textContent = '✓ Done';
      }
      this.btnPausePipeline.disabled = true;
      this.btnStopPipeline.disabled = true;
    }

    if (job.status === 'failed') {
      this.btnPausePipeline.disabled = true;
      this.btnStopPipeline.disabled = true;
    }

    // Update Logs
    if (job.logs && job.logs.length) {
      this.logItemCount.textContent = `${job.logs.length} messages`;
      this.pipelineLogsContainer.innerHTML = job.logs.map(l => {
        const isErr = l.includes('❌') || l.includes('Error') || l.includes('🛑');
        const isSuccess = l.includes('✓') || l.includes('🎉');
        const isPause = l.includes('⏸') || l.includes('▶');
        const cls = isErr ? 'error' : isSuccess ? 'success' : isPause ? 'info' : 'info';
        return `<div class="log-line ${cls}">${this.escapeHtml(l)}</div>`;
      }).join('');
      this.pipelineLogsContainer.scrollTop = this.pipelineLogsContainer.scrollHeight;
    }

    // On Completed
    if (job.status === 'completed' && job.result) {
      this.pipelineSuccessBanner.classList.remove('hidden');
      this.successTitle.textContent = `${job.result.title} Ready!`;
      this.successMeta.textContent = `Master M4B: ${job.result.size_mb} MB • AAC High Quality`;
      this.btnPipelineDownloadM4B.href = job.result.download_url;
    }
  }

  resetStepCards() {
    for (let s = 1; s <= 4; s++) {
      const card = document.getElementById(`stepCard${s}`);
      const tag = document.getElementById(`step${s}Status`);
      if (card && tag) {
        card.className = s === 1 ? 'step-card active' : 'step-card';
        tag.className = s === 1 ? 'step-status-tag active' : 'step-status-tag';
        tag.textContent = s === 1 ? 'Active' : 'Pending';
      }
    }
  }

  closeProgressModal() {
    this.modalPipelineProgress.classList.add('hidden');
  }

  // ─────────────────────────────────────────────────────────────
  // Tab Switching & Mobile Menu Controls
  // ─────────────────────────────────────────────────────────────
  toggleMobileMenu() {
    if (!this.headerCollapsibleMenu) return;
    const isOpen = this.headerCollapsibleMenu.classList.toggle('is-open');
    if (this.btnMobileMenuToggle) {
      this.btnMobileMenuToggle.classList.toggle('is-open', isOpen);
    }
  }

  closeMobileMenu() {
    if (this.headerCollapsibleMenu) {
      this.headerCollapsibleMenu.classList.remove('is-open');
    }
    if (this.btnMobileMenuToggle) {
      this.btnMobileMenuToggle.classList.remove('is-open');
    }
  }

  switchTab(tabKey) {
    this.closeMobileMenu();
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
  // Chapter Script Loading & Table Rendering
  // ─────────────────────────────────────────────────────────────
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

    this.state.playbackMode = 'script';
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
          this.state.playbackMode = 'script';
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
    if (this.state.playbackMode === 'script' && this.state.continuousPlay && this.state.activeLineIndex >= 0 && this.state.activeLineIndex < this.state.segments.length - 1) {
      this.playLineByIndex(this.state.activeLineIndex + 1);
    } else {
      this.state.isPlaying = false;
      this.state.playbackMode = 'script';
      this.btnPlayPause.textContent = '▶';
    }
  }

  togglePlayPause() {
    if (!this.audioPlayer.src) {
      if (this.state.segments.length) {
        this.state.playbackMode = 'script';
        this.playLineByIndex(0);
      }
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
    if (this.state.playbackMode === 'script' && this.state.activeLineIndex > 0) {
      this.playLineByIndex(this.state.activeLineIndex - 1);
    }
  }

  playNextLine() {
    if (this.state.playbackMode === 'script' && this.state.activeLineIndex >= 0 && this.state.activeLineIndex < this.state.segments.length - 1) {
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
  // Voice Casting & Character Discovery
  // ─────────────────────────────────────────────────────────────
  async loadVoiceBank() {
    await this.detectProjectCharacters();
  }

  async detectProjectCharacters() {
    this.detectedCharBadge.className = 'status-pill info';
    this.detectedCharBadge.textContent = 'Scanning characters in book...';
    try {
      const resp = await fetch(`/api/projects/${this.state.activeProject}/characters`);
      const data = await resp.json();
      this.state.detectedCharacters = data.characters || [];
      this.state.availableSamples = data.available_samples || [];

      this.renderDetectedCharacters(this.state.detectedCharacters);
      this.detectedCharBadge.className = 'status-pill online';
      this.detectedCharBadge.textContent = `✓ Detected ${this.state.detectedCharacters.length} Characters`;
    } catch (e) {
      console.error('Failed to detect characters:', e);
      this.detectedCharBadge.className = 'status-pill offline';
      this.detectedCharBadge.textContent = 'Character scan failed';
    }
  }

  renderDetectedCharacters(characters) {
    this.castCardsGrid.innerHTML = '';
    
    const sampleOptions = this.state.availableSamples.map(s => {
      return `<option value="${s.name}">${s.name} (${s.label})</option>`;
    }).join('');

    characters.forEach(char => {
      const cLower = char.name.toLowerCase().replace(/[^a-z0-9]/g, '');
      const assigned = char.assigned_voice || char.suggested_voice || 'narrador.wav';
      const pctText = char.pct_of_dialogue ? ` • ${char.pct_of_dialogue}% of dialogue` : '';

      const card = document.createElement('div');
      card.className = 'cast-card';
      card.innerHTML = `
        <div class="cast-card-top">
          <div class="cast-name-group">
            <span class="cast-name">${this.escapeHtml(char.name)}</span>
            <span class="char-dialogue-badge">${char.dialogue_count} lines${pctText}</span>
          </div>
          <span class="speaker-badge speaker-${cLower}">${this.escapeHtml(char.name)}</span>
        </div>

        <div class="char-quote-box">
          "${this.escapeHtml(char.sample_quote)}"
        </div>

        <div class="form-group">
          <label>Reference Voice Sample:</label>
          <select class="studio-select cast-sample-select" data-char="${this.escapeHtml(char.name)}">
            ${sampleOptions}
          </select>
        </div>

        <div class="cast-audio-row">
          <button class="btn-icon btn-audition-sample" title="Audition Reference Voice">
            ▶
          </button>
          <span class="sample-name">${assigned}</span>
        </div>
      `;

      const select = card.querySelector('.cast-sample-select');
      select.value = assigned;

      const sampleNameSpan = card.querySelector('.sample-name');
      select.addEventListener('change', (e) => {
        sampleNameSpan.textContent = e.target.value;
      });

      const btnAudition = card.querySelector('.btn-audition-sample');
      btnAudition.addEventListener('click', () => {
        this.state.playbackMode = 'sample';
        this.state.activeLineIndex = -1;
        document.querySelectorAll('.script-row').forEach(r => r.classList.remove('active-playing'));

        const sampleUrl = `/api/audio/sample?name=${encodeURIComponent(select.value)}`;
        this.audioPlayer.src = sampleUrl;
        this.audioPlayer.play();
        this.state.isPlaying = true;
        this.playerSpeaker.textContent = char.name;
        this.playerLineText.textContent = `Auditioning voice clip: ${select.value}`;
        this.btnPlayPause.textContent = '⏸';
      });

      this.castCardsGrid.appendChild(card);
    });
  }

  async saveBatchVoiceCasting() {
    this.btnSaveVoiceCasting.textContent = '⚙ Saving...';
    try {
      const assignments = {};
      document.querySelectorAll('.cast-sample-select').forEach(sel => {
        const charName = sel.getAttribute('data-char');
        assignments[charName] = sel.value;
      });

      const resp = await fetch(`/api/projects/${this.state.activeProject}/cast_all`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assignments })
      });

      const data = await resp.json();
      this.btnSaveVoiceCasting.innerHTML = '<span>💾</span> Save Casting';
      if (data.success) {
        alert(`✓ Voice casting updated for ${data.updated_characters} character(s)!`);
      }
    } catch (e) {
      this.btnSaveVoiceCasting.innerHTML = '<span>💾</span> Save Casting';
      alert('Failed to save voice casting.');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Packaging & M4B Compilation
  // ─────────────────────────────────────────────────────────────
  updatePackagingMetadata() {
    const curProj = this.state.projectsList.find(p => p.id === this.state.activeProject);
    if (curProj) {
      this.txtBookTitle.value = `${curProj.name} (Audiobook)`;
      this.txtAuthor.value = 'Tappei Nagatsuki';
      const coverPath = `${curProj.output_dir}/cover.jpg`;
      this.txtCoverPath.value = coverPath;
      this.coverPreviewImg.src = `/api/audio/download?path=${encodeURIComponent(coverPath)}`;
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

  async synthesizeActiveChapter() {
    this.btnSynthesizeChapter.textContent = '⚙ Synthesizing...';
    try {
      const payload = {
        project_id: this.state.activeProject,
        chapter_id: this.state.activeChapter,
        engine: 'omnivoice',
        mode: this.state.engineMode,
        remote_url: this.state.remoteUrl,
        workers: 4
      };
      const resp = await fetch('/api/tasks/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      this.btnSynthesizeChapter.innerHTML = '<span>⚡</span> Synthesize Chapter';
      if (data.success) {
        await this.loadChapterScript(this.state.activeChapter);
        alert(`Chapter synthesized! (${data.newly_generated} lines generated, ${data.already_cached} cached)`);
      }
    } catch (e) {
      this.btnSynthesizeChapter.innerHTML = '<span>⚡</span> Synthesize Chapter';
      alert('Synthesis failed.');
    }
  }

  async synthesizeAllChapters() {
    this.btnSynthesizeAllChapters.textContent = '⚙ Synthesizing All...';
    try {
      const payload = {
        project_id: this.state.activeProject,
        engine: 'omnivoice',
        mode: this.state.engineMode,
        remote_url: this.state.remoteUrl,
        workers: 4
      };
      const resp = await fetch('/api/tasks/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await resp.json();
      this.btnSynthesizeAllChapters.innerHTML = '<span>⚡</span> Synthesize All Missing Lines';
      if (data.success) {
        await this.loadProject();
        this.renderChapterChecklist();
        alert(`All chapters synthesized! (${data.newly_generated} lines generated, ${data.already_cached} cached)`);
      }
    } catch (e) {
      this.btnSynthesizeAllChapters.innerHTML = '<span>⚡</span> Synthesize All Missing Lines';
      alert('Batch synthesis failed.');
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
