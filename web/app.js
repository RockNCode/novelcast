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
      selectedNewProjectType: 'epub',
      librarySamples: [],
      libraryCharacters: {},
      libraryFilterCategory: 'all',
      libraryFilterGender: 'all',
      librarySearchQuery: '',
      activeVoiceDeck: 'casting',
      llmConfig: null,
      selectedSettingsProvider: 'ollama'
    };

    this.audioPlayer = document.getElementById('globalAudioPlayer');
    this.selectedUploadFile = null;
    this.editingProfileName = null;
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

    // Tab 2: Voice Casting & Voice Bank Manager
    this.subtabCasting = document.getElementById('subtabCasting');
    this.subtabLibrary = document.getElementById('subtabLibrary');
    this.deckCharacterCasting = document.getElementById('deckCharacterCasting');
    this.deckVoiceLibrary = document.getElementById('deckVoiceLibrary');
    this.countLibraryTotal = document.getElementById('countLibraryTotal');
    this.inputVoiceSearch = document.getElementById('inputVoiceSearch');
    this.voiceCategoryFilters = document.getElementById('voiceCategoryFilters');
    this.voiceGenderFilters = document.getElementById('voiceGenderFilters');
    this.voiceLibraryGrid = document.getElementById('voiceLibraryGrid');
    this.btnOpenUploadModal = document.getElementById('btnOpenUploadModal');
    this.btnOpenProfileModal = document.getElementById('btnOpenProfileModal');
    this.castCardsGrid = document.getElementById('castCardsGrid');
    this.btnRefreshVoices = document.getElementById('btnRefreshVoices');
    this.btnAutoDetectCharacters = document.getElementById('btnAutoDetectCharacters');
    this.btnSaveVoiceCasting = document.getElementById('btnSaveVoiceCasting');
    this.detectedCharBadge = document.getElementById('detectedCharBadge');

    // Upload Voice Modal
    this.modalUploadVoice = document.getElementById('modalUploadVoice');
    this.btnCloseUploadVoiceModal = document.getElementById('btnCloseUploadVoiceModal');
    this.btnCancelUploadVoice = document.getElementById('btnCancelUploadVoice');
    this.voiceDropzone = document.getElementById('voiceDropzone');
    this.inputVoiceFile = document.getElementById('inputVoiceFile');
    this.btnBrowseVoiceFile = document.getElementById('btnBrowseVoiceFile');
    this.uploadPreviewSection = document.getElementById('uploadPreviewSection');
    this.uploadPreviewFilename = document.getElementById('uploadPreviewFilename');
    this.uploadPreviewFilesize = document.getElementById('uploadPreviewFilesize');
    this.audioUploadPreview = document.getElementById('audioUploadPreview');
    this.inputUploadVoiceName = document.getElementById('inputUploadVoiceName');
    this.selectUploadCategory = document.getElementById('selectUploadCategory');
    this.selectUploadGender = document.getElementById('selectUploadGender');
    this.inputUploadInstruct = document.getElementById('inputUploadInstruct');
    this.inputUploadDescription = document.getElementById('inputUploadDescription');
    this.btnSubmitUploadVoice = document.getElementById('btnSubmitUploadVoice');

    // Voice Profile Modal
    this.modalVoiceProfile = document.getElementById('modalVoiceProfile');
    this.profileModalTitle = document.getElementById('profileModalTitle');
    this.btnCloseProfileModal = document.getElementById('btnCloseProfileModal');
    this.btnCancelProfile = document.getElementById('btnCancelProfile');
    this.inputProfileName = document.getElementById('inputProfileName');
    this.selectProfileGender = document.getElementById('selectProfileGender');
    this.selectProfileRefAudio = document.getElementById('selectProfileRefAudio');
    this.inputProfileInstruct = document.getElementById('inputProfileInstruct');
    this.sliderProfileSpeed = document.getElementById('sliderProfileSpeed');
    this.valProfileSpeed = document.getElementById('valProfileSpeed');
    this.sliderProfileGuidance = document.getElementById('sliderProfileGuidance');
    this.valProfileGuidance = document.getElementById('valProfileGuidance');
    this.inputProfileDescription = document.getElementById('inputProfileDescription');
    this.btnDeleteProfile = document.getElementById('btnDeleteProfile');
    this.btnSubmitProfile = document.getElementById('btnSubmitProfile');

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

    // Tab 5: Settings & LLM Engine Elements
    this.llmProviderList = document.getElementById('llmProviderList');
    this.labelActiveLLM = document.getElementById('labelActiveLLM');
    this.badgeActiveLLMStatus = document.getElementById('badgeActiveLLMStatus');
    this.currentProviderTitle = document.getElementById('currentProviderTitle');
    this.currentProviderDesc = document.getElementById('currentProviderDesc');
    this.btnSetAsDefaultProvider = document.getElementById('btnSetAsDefaultProvider');
    this.inputLLMAPIBase = document.getElementById('inputLLMAPIBase');
    this.inputLLMAPIKey = document.getElementById('inputLLMAPIKey');
    this.inputLLMTimeout = document.getElementById('inputLLMTimeout');
    this.selectLLMDefaultModel = document.getElementById('selectLLMDefaultModel');
    this.inputLLMCustomModel = document.getElementById('inputLLMCustomModel');
    this.sliderLLMTemperature = document.getElementById('sliderLLMTemperature');
    this.valLLMTemperature = document.getElementById('valLLMTemperature');
    this.btnTestLLMConnection = document.getElementById('btnTestLLMConnection');
    this.testResultPill = document.getElementById('testResultPill');
    this.testResultIcon = document.getElementById('testResultIcon');
    this.testResultMsg = document.getElementById('testResultMsg');
    this.btnSaveLLMConfig = document.getElementById('btnSaveLLMConfig');

    // AI Fix Dialogue & Speakers Modal
    this.btnOpenAIFixModal = document.getElementById('btnOpenAIFixModal');
    this.modalAIFixDialogue = document.getElementById('modalAIFixDialogue');
    this.btnCloseAIFixModal = document.getElementById('btnCloseAIFixModal');
    this.btnCancelAIFix = document.getElementById('btnCancelAIFix');
    this.btnSubmitAIFix = document.getElementById('btnSubmitAIFix');
    this.selectAIFixProvider = document.getElementById('selectAIFixProvider');
    this.selectAIFixModel = document.getElementById('selectAIFixModel');
    this.aiFixCurrentChapterName = document.getElementById('aiFixCurrentChapterName');
    this.chkAIFixSpeakers = document.getElementById('chkAIFixSpeakers');
    this.chkAIFixInstructs = document.getElementById('chkAIFixInstructs');
    this.chkAIFixTokens = document.getElementById('chkAIFixTokens');
    this.inputAIFixStoryLore = document.getElementById('inputAIFixStoryLore');
    this.aiFixProgressSection = document.getElementById('aiFixProgressSection');
    this.aiFixStatusText = document.getElementById('aiFixStatusText');
    this.aiFixProgressPct = document.getElementById('aiFixProgressPct');
    this.aiFixProgressBar = document.getElementById('aiFixProgressBar');
    this.aiFixDiffList = document.getElementById('aiFixDiffList');
    this.aiFixChangesCount = document.getElementById('aiFixChangesCount');

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

    // Voice Bank Sub-Nav Switcher
    if (this.subtabCasting) {
      this.subtabCasting.addEventListener('click', () => this.switchVoiceDeck('casting'));
    }
    if (this.subtabLibrary) {
      this.subtabLibrary.addEventListener('click', () => this.switchVoiceDeck('library'));
    }

    // Voice Bank Upload Modal Events
    if (this.btnOpenUploadModal) {
      this.btnOpenUploadModal.addEventListener('click', () => this.openUploadVoiceModal());
    }
    if (this.btnCloseUploadVoiceModal) {
      this.btnCloseUploadVoiceModal.addEventListener('click', () => this.closeUploadVoiceModal());
    }
    if (this.btnCancelUploadVoice) {
      this.btnCancelUploadVoice.addEventListener('click', () => this.closeUploadVoiceModal());
    }
    if (this.btnBrowseVoiceFile) {
      this.btnBrowseVoiceFile.addEventListener('click', () => this.inputVoiceFile.click());
    }
    if (this.inputVoiceFile) {
      this.inputVoiceFile.addEventListener('change', (e) => {
        if (e.target.files && e.target.files[0]) {
          this.handleVoiceFileSelect(e.target.files[0]);
        }
      });
    }

    // Voice Dropzone Drag & Drop
    if (this.voiceDropzone) {
      this.voiceDropzone.addEventListener('dragover', (e) => {
        e.preventDefault();
        this.voiceDropzone.classList.add('dragover');
      });
      this.voiceDropzone.addEventListener('dragleave', () => {
        this.voiceDropzone.classList.remove('dragover');
      });
      this.voiceDropzone.addEventListener('drop', (e) => {
        e.preventDefault();
        this.voiceDropzone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
          this.handleVoiceFileSelect(e.dataTransfer.files[0]);
        }
      });
    }

    if (this.btnSubmitUploadVoice) {
      this.btnSubmitUploadVoice.addEventListener('click', () => this.submitVoiceUpload());
    }

    // Voice Profile Modal Events
    if (this.btnOpenProfileModal) {
      this.btnOpenProfileModal.addEventListener('click', () => this.openVoiceProfileModal());
    }
    if (this.btnCloseProfileModal) {
      this.btnCloseProfileModal.addEventListener('click', () => this.closeVoiceProfileModal());
    }
    if (this.btnCancelProfile) {
      this.btnCancelProfile.addEventListener('click', () => this.closeVoiceProfileModal());
    }
    if (this.sliderProfileSpeed) {
      this.sliderProfileSpeed.addEventListener('input', (e) => {
        this.valProfileSpeed.textContent = e.target.value;
      });
    }
    if (this.sliderProfileGuidance) {
      this.sliderProfileGuidance.addEventListener('input', (e) => {
        this.valProfileGuidance.textContent = e.target.value;
      });
    }
    if (this.btnSubmitProfile) {
      this.btnSubmitProfile.addEventListener('click', () => this.submitVoiceProfile());
    }
    if (this.btnDeleteProfile) {
      this.btnDeleteProfile.addEventListener('click', () => this.deleteCurrentEditingProfile());
    }

    // Voice Library Search & Filter Events
    if (this.inputVoiceSearch) {
      this.inputVoiceSearch.addEventListener('input', (e) => {
        this.state.librarySearchQuery = e.target.value.toLowerCase().trim();
        this.renderVoiceLibrary();
      });
    }
    if (this.voiceCategoryFilters) {
      this.voiceCategoryFilters.querySelectorAll('.filter-pill').forEach(pill => {
        pill.addEventListener('click', () => {
          this.voiceCategoryFilters.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
          pill.classList.add('active');
          this.state.libraryFilterCategory = pill.getAttribute('data-category');
          this.renderVoiceLibrary();
        });
      });
    }
    if (this.voiceGenderFilters) {
      this.voiceGenderFilters.querySelectorAll('.filter-pill').forEach(pill => {
        pill.addEventListener('click', () => {
          this.voiceGenderFilters.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
          pill.classList.add('active');
          this.state.libraryFilterGender = pill.getAttribute('data-gender');
          this.renderVoiceLibrary();
        });
      });
    }

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

    // Settings & LLM Events
    this.btnSetAsDefaultProvider?.addEventListener('click', () => this.setActiveLLMProvider());
    this.btnTestLLMConnection?.addEventListener('click', () => this.testCurrentLLMConnection());
    this.btnSaveLLMConfig?.addEventListener('click', () => this.saveCurrentLLMConfig());
    this.sliderLLMTemperature?.addEventListener('input', (e) => {
      this.valLLMTemperature.textContent = e.target.value;
    });
    this.selectLLMDefaultModel?.addEventListener('change', (e) => {
      if (e.target.value === '__custom__') {
        this.inputLLMCustomModel.classList.remove('hidden');
        this.inputLLMCustomModel.focus();
      } else {
        this.inputLLMCustomModel.classList.add('hidden');
      }
    });

    // AI Fix Dialogue Modal Events
    this.btnOpenAIFixModal?.addEventListener('click', () => this.openAIFixModal());
    this.btnCloseAIFixModal?.addEventListener('click', () => this.closeAIFixModal());
    this.btnCancelAIFix?.addEventListener('click', () => this.closeAIFixModal());
    this.btnSubmitAIFix?.addEventListener('click', () => this.submitAIFix());
    this.selectAIFixProvider?.addEventListener('change', (e) => {
      this.populateAIFixModels(e.target.value);
    });

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
    await this.loadLLMConfig();
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
      dubbingStudio: 'tabDubbingStudio',
      settingsStudio: 'tabSettingsStudio'
    };

    this.tabPanels.forEach(p => {
      p.classList.toggle('active', p.id === panelMap[tabKey]);
    });

    if (tabKey === 'packagingStudio') {
      this.renderChapterChecklist();
    } else if (tabKey === 'settingsStudio') {
      this.loadLLMConfig();
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
    const speakerSet = new Set(['Narrador']);
    
    // Add all detected & custom characters in project
    (this.state.detectedCharacters || []).forEach(c => speakerSet.add(c.name));
    
    // Add all characters in voice library
    Object.keys(this.state.libraryCharacters || {}).forEach(k => speakerSet.add(k));

    // Ensure current speaker is in set
    if (currentSpeaker) {
      speakerSet.add(currentSpeaker);
    }

    const sorted = Array.from(speakerSet).sort((a, b) => {
      if (a === 'Narrador') return -1;
      if (b === 'Narrador') return 1;
      return a.localeCompare(b);
    });

    let opts = '';
    sorted.forEach(s => {
      const sel = (s.toLowerCase() === (currentSpeaker || '').toLowerCase()) ? 'selected' : '';
      opts += `<option value="${this.escapeHtml(s)}" ${sel}>${this.escapeHtml(s)}</option>`;
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
  // Voice Casting & Voice Bank Manager Deck
  // ─────────────────────────────────────────────────────────────
  switchVoiceDeck(deckName) {
    this.state.activeVoiceDeck = deckName;
    if (deckName === 'casting') {
      this.subtabCasting?.classList.add('active');
      this.subtabLibrary?.classList.remove('active');
      this.deckCharacterCasting?.classList.remove('hidden');
      this.deckVoiceLibrary?.classList.add('hidden');
    } else {
      this.subtabLibrary?.classList.add('active');
      this.subtabCasting?.classList.remove('active');
      this.deckVoiceLibrary?.classList.remove('hidden');
      this.deckCharacterCasting?.classList.add('hidden');
      this.renderVoiceLibrary();
    }
  }

  async loadVoiceBank() {
    await Promise.all([
      this.detectProjectCharacters(),
      this.loadVoiceBankLibrary()
    ]);
  }

  async loadVoiceBankLibrary() {
    try {
      const resp = await fetch('/api/voice-bank/library');
      const data = await resp.json();
      this.state.librarySamples = data.samples || [];
      this.state.libraryCharacters = data.characters || {};
      
      if (this.countLibraryTotal) {
        this.countLibraryTotal.textContent = this.state.librarySamples.length;
      }

      this.renderVoiceLibrary();
    } catch (e) {
      console.error('Failed to load voice bank library:', e);
    }
  }

  renderVoiceLibrary() {
    if (!this.voiceLibraryGrid) return;
    this.voiceLibraryGrid.innerHTML = '';

    const query = this.state.librarySearchQuery || '';
    const catFilter = this.state.libraryFilterCategory || 'all';
    const genderFilter = this.state.libraryFilterGender || 'all';

    const filtered = this.state.librarySamples.filter(sample => {
      // 1. Search Query Filter
      if (query) {
        const matchesName = sample.name.toLowerCase().includes(query);
        const matchesLabel = sample.label.toLowerCase().includes(query);
        const matchesChar = (sample.assigned_characters || []).some(c => c.toLowerCase().includes(query));
        if (!matchesName && !matchesLabel && !matchesChar) return false;
      }

      // 2. Category Filter
      if (catFilter !== 'all') {
        if (catFilter === 'Custom' && !sample.category.includes('Custom')) return false;
        if (catFilter === 'Master Bank' && !sample.category.includes('Master')) return false;
        if (catFilter === 'ElevenLabs Archive' && !sample.category.includes('ElevenLabs')) return false;
        if (catFilter === 'Default / Root' && !sample.category.includes('Default') && !sample.category.includes('Root')) return false;
      }

      // 3. Gender Filter
      if (genderFilter !== 'all') {
        const boundProfile = (sample.assigned_characters || []).map(c => this.state.libraryCharacters[c]).find(p => p);
        const sampleGender = (boundProfile?.gender || '').toLowerCase();
        if (sampleGender !== genderFilter && sampleGender !== 'unspecified') return false;
      }

      return true;
    });

    if (filtered.length === 0) {
      this.voiceLibraryGrid.innerHTML = `
        <div class="empty-library-state glass-panel" style="grid-column: 1 / -1; padding: 3rem; text-align: center;">
          <div style="font-size: 2.5rem; margin-bottom: 0.75rem;">🎙️</div>
          <h3>No Voice Samples Match Current Filter</h3>
          <p class="panel-desc">Try changing your search keywords or click "Upload Voice Sample" to add new clips.</p>
        </div>
      `;
      return;
    }

    filtered.forEach(sample => {
      // Category Badge Class
      let catClass = 'cat-default';
      if (sample.category.includes('ElevenLabs')) catClass = 'cat-elevenlabs';
      else if (sample.category.includes('Master')) catClass = 'cat-master';
      else if (sample.category.includes('Custom')) catClass = 'cat-custom';

      // Find bound profile details
      const primaryChar = (sample.assigned_characters && sample.assigned_characters[0]) || null;
      const profile = primaryChar ? this.state.libraryCharacters[primaryChar] : null;
      const gender = profile?.gender || 'unspecified';
      const instruct = profile?.instruct || null;

      const card = document.createElement('div');
      card.className = 'voice-library-card';
      card.innerHTML = `
        <div class="voice-card-header">
          <div class="voice-card-title-group">
            <span class="voice-card-title">${this.escapeHtml(primaryChar || sample.label)}</span>
            <span class="voice-card-filename">${this.escapeHtml(sample.name)}</span>
          </div>
          <span class="voice-badge ${catClass}">${this.escapeHtml(sample.category)}</span>
        </div>

        <div class="voice-card-tags">
          <span class="voice-tag">📊 ${sample.size_kb} KB</span>
          ${gender !== 'unspecified' ? `<span class="voice-tag">⚧ ${gender}</span>` : ''}
          ${primaryChar ? `<span class="voice-tag" style="color: var(--accent-color);">👤 Bound: ${this.escapeHtml(primaryChar)}</span>` : '<span class="voice-tag" style="color: var(--text-muted);">Unbound Clip</span>'}
        </div>

        ${instruct ? `<div class="char-quote-box" style="font-size: 0.75rem; padding: 0.4rem 0.6rem;">Delivery: <em>"${this.escapeHtml(instruct)}"</em></div>` : ''}

        <div class="voice-card-audio">
          <button class="btn-audition-card btn-audition-library" title="Play Voice Sample">
            ▶
          </button>
          <span class="voice-card-meta-text">${sample.filename}</span>
        </div>

        <div class="voice-card-actions">
          <button class="btn btn-secondary btn-sm btn-edit-profile" title="Configure voice profile delivery parameters">
            <span>✏️</span> Edit Profile
          </button>
          <button class="btn btn-danger btn-sm btn-delete-sample" title="Delete voice audio file">
            <span>🗑️</span>
          </button>
        </div>
      `;

      // Play sample button
      const btnPlay = card.querySelector('.btn-audition-library');
      btnPlay.addEventListener('click', () => {
        this.state.playbackMode = 'sample';
        this.state.activeLineIndex = -1;
        document.querySelectorAll('.script-row').forEach(r => r.classList.remove('active-playing'));

        this.audioPlayer.src = sample.audio_url;
        this.audioPlayer.play();
        this.state.isPlaying = true;
        this.playerSpeaker.textContent = primaryChar || sample.label;
        this.playerLineText.textContent = `Auditioning voice library sample: ${sample.name}`;
        this.btnPlayPause.textContent = '⏸';
      });

      // Edit profile button
      const btnEdit = card.querySelector('.btn-edit-profile');
      btnEdit.addEventListener('click', () => {
        this.openVoiceProfileModal(primaryChar, sample.name);
      });

      // Delete sample button
      const btnDelete = card.querySelector('.btn-delete-sample');
      btnDelete.addEventListener('click', () => {
        this.deleteVoiceSample(sample.name);
      });

      this.voiceLibraryGrid.appendChild(card);
    });
  }

  // ─────────────────────────────────────────────────────────────
  // Upload Voice Sample Modal
  // ─────────────────────────────────────────────────────────────
  openUploadVoiceModal() {
    if (!this.modalUploadVoice) return;
    this.selectedUploadFile = null;
    this.inputVoiceFile.value = '';
    this.inputUploadVoiceName.value = '';
    this.inputUploadInstruct.value = '';
    this.inputUploadDescription.value = '';
    this.selectUploadCategory.value = 'custom';
    this.selectUploadGender.value = 'unspecified';
    this.uploadPreviewSection.classList.add('hidden');
    this.audioUploadPreview.src = '';
    this.modalUploadVoice.classList.remove('hidden');
  }

  closeUploadVoiceModal() {
    if (!this.modalUploadVoice) return;
    this.modalUploadVoice.classList.add('hidden');
    this.audioUploadPreview.pause();
    this.audioUploadPreview.src = '';
  }

  handleVoiceFileSelect(file) {
    if (!file) return;
    this.selectedUploadFile = file;

    // Auto-suggest name from file
    if (!this.inputUploadVoiceName.value) {
      const baseName = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
      this.inputUploadVoiceName.value = baseName.replace(/[_\-]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    this.uploadPreviewFilename.textContent = file.name;
    this.uploadPreviewFilesize.textContent = `${Math.round(file.size / 1024)} KB`;
    this.audioUploadPreview.src = URL.createObjectURL(file);
    this.uploadPreviewSection.classList.remove('hidden');
  }

  async submitVoiceUpload() {
    if (!this.selectedUploadFile) {
      alert('Please select or drop an audio file (.wav, .mp3, .flac) to upload.');
      return;
    }

    const voiceName = this.inputUploadVoiceName.value.trim();
    if (!voiceName) {
      alert('Please enter a Character / Speaker Name for this voice.');
      return;
    }

    this.btnSubmitUploadVoice.disabled = true;
    this.btnSubmitUploadVoice.textContent = '⏳ Uploading & Registering...';

    try {
      const formData = new FormData();
      formData.append('file', this.selectedUploadFile);
      formData.append('voice_name', voiceName);
      formData.append('category', this.selectUploadCategory.value);
      formData.append('gender', this.selectUploadGender.value);
      formData.append('instruct', this.inputUploadInstruct.value.trim() || '');
      formData.append('description', this.inputUploadDescription.value.trim() || '');

      const resp = await fetch('/api/voice-bank/upload', {
        method: 'POST',
        body: formData
      });

      const data = await resp.json();
      this.btnSubmitUploadVoice.disabled = false;
      this.btnSubmitUploadVoice.innerHTML = '<span>🚀</span> Upload & Register Voice';

      if (data.success) {
        alert(`✓ Voice sample "${voiceName}" uploaded and registered successfully!`);
        this.closeUploadVoiceModal();
        await this.loadVoiceBankLibrary();
        await this.detectProjectCharacters();
      } else {
        alert(`Upload failed: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error('Failed to upload voice:', e);
      this.btnSubmitUploadVoice.disabled = false;
      this.btnSubmitUploadVoice.innerHTML = '<span>🚀</span> Upload & Register Voice';
      alert('Failed to upload voice sample.');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // Character Voice Profile Modal
  // ─────────────────────────────────────────────────────────────
  openVoiceProfileModal(charName = null, defaultSamplePath = null) {
    if (!this.modalVoiceProfile) return;
    this.editingProfileName = charName;

    // Populate Sample Options
    this.selectProfileRefAudio.innerHTML = '';
    this.state.librarySamples.forEach(s => {
      const opt = document.createElement('option');
      opt.value = s.name;
      opt.textContent = `${s.name} (${s.label})`;
      this.selectProfileRefAudio.appendChild(opt);
    });

    if (charName && this.state.libraryCharacters[charName]) {
      const prof = this.state.libraryCharacters[charName];
      this.profileModalTitle.textContent = `👤 Edit Profile: ${charName}`;
      this.inputProfileName.value = charName;
      this.inputProfileName.disabled = true; // Key immutable during edit
      this.selectProfileGender.value = prof.gender || 'unspecified';
      this.inputProfileInstruct.value = prof.instruct || '';
      this.sliderProfileSpeed.value = prof.speed || 1.0;
      this.valProfileSpeed.textContent = prof.speed || 1.0;
      this.sliderProfileGuidance.value = prof.guidance_scale || 2.8;
      this.valProfileGuidance.textContent = prof.guidance_scale || 2.8;
      this.inputProfileDescription.value = prof.description || '';

      // Match reference audio
      const ref = prof.reference_audio ? prof.reference_audio.replace(/^voice_bank\//, '') : '';
      this.selectProfileRefAudio.value = ref || (defaultSamplePath || '');
      this.btnDeleteProfile.classList.remove('hidden');
    } else {
      this.profileModalTitle.textContent = '👤 Create New Voice Profile';
      this.inputProfileName.value = charName || '';
      this.inputProfileName.disabled = false;
      this.selectProfileGender.value = 'female';
      this.inputProfileInstruct.value = '';
      this.sliderProfileSpeed.value = 1.0;
      this.valProfileSpeed.textContent = '1.0';
      this.sliderProfileGuidance.value = 2.8;
      this.valProfileGuidance.textContent = '2.8';
      this.inputProfileDescription.value = '';
      if (defaultSamplePath) {
        this.selectProfileRefAudio.value = defaultSamplePath;
      }
      this.btnDeleteProfile.classList.add('hidden');
    }

    this.modalVoiceProfile.classList.remove('hidden');
  }

  closeVoiceProfileModal() {
    if (!this.modalVoiceProfile) return;
    this.modalVoiceProfile.classList.add('hidden');
    this.editingProfileName = null;
  }

  async submitVoiceProfile() {
    const charName = this.inputProfileName.value.trim();
    const sample = this.selectProfileRefAudio.value;

    if (!charName) {
      alert('Please enter a Character Name.');
      return;
    }
    if (!sample) {
      alert('Please select a Reference Audio Sample.');
      return;
    }

    this.btnSubmitProfile.disabled = true;
    this.btnSubmitProfile.textContent = 'Saving...';

    try {
      const payload = {
        name: charName,
        reference_audio: sample,
        gender: this.selectProfileGender.value,
        instruct: this.inputProfileInstruct.value.trim() || null,
        speed: parseFloat(this.sliderProfileSpeed.value) || 1.0,
        guidance_scale: parseFloat(this.sliderProfileGuidance.value) || 2.8,
        description: this.inputProfileDescription.value.trim() || null
      };

      const resp = await fetch('/api/voice-bank/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      const data = await resp.json();
      this.btnSubmitProfile.disabled = false;
      this.btnSubmitProfile.innerHTML = '<span>💾</span> Save Voice Profile';

      if (data.success) {
        alert(`✓ Voice Profile for "${charName}" saved successfully!`);
        this.closeVoiceProfileModal();
        await this.loadVoiceBankLibrary();
        await this.detectProjectCharacters();
      } else {
        alert(`Failed to save profile: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error('Failed to save profile:', e);
      this.btnSubmitProfile.disabled = false;
      this.btnSubmitProfile.innerHTML = '<span>💾</span> Save Voice Profile';
      alert('Failed to save profile.');
    }
  }

  async deleteCurrentEditingProfile() {
    if (!this.editingProfileName) return;
    if (!confirm(`Are you sure you want to delete voice profile for "${this.editingProfileName}"?`)) {
      return;
    }

    try {
      const resp = await fetch(`/api/voice-bank/profiles/${encodeURIComponent(this.editingProfileName)}`, {
        method: 'DELETE'
      });
      const data = await resp.json();
      if (data.success) {
        alert(`✓ Profile "${this.editingProfileName}" deleted.`);
        this.closeVoiceProfileModal();
        await this.loadVoiceBankLibrary();
        await this.detectProjectCharacters();
      } else {
        alert(`Failed to delete profile: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error('Failed to delete profile:', e);
      alert('Failed to delete profile.');
    }
  }

  async deleteVoiceSample(sampleName) {
    if (!confirm(`Are you sure you want to delete audio sample "${sampleName}" from the Voice Bank?\n\nThis will remove the file from disk.`)) {
      return;
    }

    try {
      const resp = await fetch(`/api/voice-bank/samples?name=${encodeURIComponent(sampleName)}`, {
        method: 'DELETE'
      });
      const data = await resp.json();
      if (data.success) {
        alert(`✓ Voice sample "${sampleName}" deleted from Voice Bank.`);
        await this.loadVoiceBankLibrary();
        await this.detectProjectCharacters();
      } else {
        alert(`Failed to delete voice sample: ${data.detail || 'Unknown error'}`);
      }
    } catch (e) {
      console.error('Failed to delete voice sample:', e);
      alert('Failed to delete voice sample.');
    }
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
    
    const sampleOptions = [
      `<option value="">-- Select a Voice Sample --</option>`,
      ...this.state.availableSamples.map(s => `<option value="${s.name}">${s.name} (${s.label})</option>`)
    ].join('');

    characters.forEach(char => {
      const cLower = char.name.toLowerCase().replace(/[^a-z0-9]/g, '');
      const assigned = char.assigned_voice || char.suggested_voice || '';
      const pctText = char.pct_of_dialogue ? ` • ${char.pct_of_dialogue}% of dialogue` : '';

      // Match against availableSamples
      let matchedValue = '';
      if (assigned) {
        const exact = this.state.availableSamples.find(s => s.name === assigned);
        if (exact) {
          matchedValue = exact.name;
        } else {
          const baseName = assigned.split('/').pop().toLowerCase();
          const match = this.state.availableSamples.find(s => {
            const sBase = s.name.split('/').pop().toLowerCase();
            return sBase === baseName || s.name.toLowerCase().endsWith('/' + baseName);
          });
          if (match) {
            matchedValue = match.name;
          }
        }
      }

      if (!matchedValue && char.name.toLowerCase() === 'narrador') {
        const narr = this.state.availableSamples.find(s => s.name.toLowerCase().includes('narrador'));
        if (narr) matchedValue = narr.name;
      }

      const isCustom = char.is_custom || char.dialogue_count === 0;
      const countBadge = isCustom
        ? `<span class="char-dialogue-badge" style="background: rgba(99, 102, 241, 0.25); color: #a5b4fc; border: 1px solid rgba(99, 102, 241, 0.4);">⭐ Pre-Cast / Custom</span>`
        : `<span class="char-dialogue-badge">${char.dialogue_count} lines${pctText}</span>`;

      const card = document.createElement('div');
      card.className = 'cast-card';
      card.innerHTML = `
        <div class="cast-card-top">
          <div class="cast-name-group">
            <span class="cast-name">${this.escapeHtml(char.name)}</span>
            ${countBadge}
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
          <span class="sample-name">${matchedValue || 'None assigned'}</span>
        </div>

        <div class="cast-card-actions" style="display: flex; gap: 0.5rem; margin-top: 0.75rem; border-top: 1px solid var(--border-glass); padding-top: 0.75rem;">
          <button class="btn btn-secondary btn-sm btn-cast-edit-prof" style="flex: 1; font-size: 0.8rem; padding: 0.35rem 0.5rem;" title="Configure delivery instruct prompt, speed, and scale">
            <span>✏️</span> Delivery & Tone
          </button>
          ${isCustom ? `
            <button class="btn btn-danger btn-sm btn-cast-delete-char" style="padding: 0.35rem 0.6rem;" title="Remove this pre-cast character">
              <span>🗑️</span>
            </button>
          ` : ''}
        </div>
      `;

      const select = card.querySelector('.cast-sample-select');
      select.value = matchedValue;

      const sampleNameSpan = card.querySelector('.sample-name');
      select.addEventListener('change', (e) => {
        sampleNameSpan.textContent = e.target.value || 'None assigned';
      });

      const btnAudition = card.querySelector('.btn-audition-sample');
      btnAudition.addEventListener('click', () => {
        if (!select.value) {
          alert('Please select a reference voice sample to audition.');
          return;
        }

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

      // Edit delivery profile
      const btnEditProf = card.querySelector('.btn-cast-edit-prof');
      btnEditProf.addEventListener('click', () => {
        this.openVoiceProfileModal(char.name, select.value);
      });

      // Delete character profile (if custom)
      const btnDelChar = card.querySelector('.btn-cast-delete-char');
      if (btnDelChar) {
        btnDelChar.addEventListener('click', async () => {
          if (!confirm(`Are you sure you want to remove pre-cast character "${char.name}"?`)) return;
          try {
            await fetch(`/api/voice-bank/profiles/${encodeURIComponent(char.name)}`, { method: 'DELETE' });
            await this.loadVoiceBankLibrary();
            await this.detectProjectCharacters();
          } catch (e) {
            console.error('Failed to remove character:', e);
          }
        });
      }

      this.castCardsGrid.appendChild(card);
    });
  }

  async saveBatchVoiceCasting() {
    this.btnSaveVoiceCasting.textContent = '⚙ Saving...';
    try {
      const assignments = {};
      document.querySelectorAll('.cast-sample-select').forEach(sel => {
        const charName = sel.getAttribute('data-char');
        if (sel.value) {
          assignments[charName] = sel.value;
        }
      });

      const resp = await fetch(`/api/projects/${this.state.activeProject}/cast_all`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ assignments })
      });

      const data = await resp.json();
      this.btnSaveVoiceCasting.innerHTML = '<span>💾</span> Save Casting';
      if (data.success) {
        await this.detectProjectCharacters();
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

  // ─────────────────────────────────────────────────────────────
  // Settings & LLM Management (Tab 5)
  // ─────────────────────────────────────────────────────────────
  async loadLLMConfig() {
    try {
      const resp = await fetch('/api/llm/config');
      this.state.llmConfig = await resp.json();
      
      const activeProvKey = this.state.llmConfig.active_provider;
      const activeProv = this.state.llmConfig.providers[activeProvKey] || {};
      const activeModel = this.state.llmConfig.active_model || activeProv.default_model || 'default';

      if (this.labelActiveLLM) {
        this.labelActiveLLM.textContent = `${activeProv.name || activeProvKey} (${activeModel})`;
      }

      this.renderSettingsProviderList();
      this.selectSettingsProvider(this.state.selectedSettingsProvider || activeProvKey);
      this.populateAIFixProviders();
      this.checkActiveLLMHealth();
    } catch (e) {
      console.error('Failed to load LLM config:', e);
    }
  }

  async checkActiveLLMHealth() {
    if (!this.badgeActiveLLMStatus || !this.state.llmConfig) return;
    const activeProvKey = this.state.llmConfig.active_provider;
    this.badgeActiveLLMStatus.className = 'status-pill info';
    this.badgeActiveLLMStatus.textContent = 'Probing LLM...';

    try {
      const resp = await fetch('/api/llm/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_id: activeProvKey, model: this.state.llmConfig.active_model })
      });
      const data = await resp.json();
      if (data.success) {
        this.badgeActiveLLMStatus.className = 'status-pill online';
        this.badgeActiveLLMStatus.textContent = `✓ Online (${data.latency_ms}ms)`;
      } else {
        this.badgeActiveLLMStatus.className = 'status-pill offline';
        this.badgeActiveLLMStatus.textContent = 'Offline / Unreachable';
      }
    } catch (e) {
      this.badgeActiveLLMStatus.className = 'status-pill offline';
      this.badgeActiveLLMStatus.textContent = 'Connection Error';
    }
  }

  renderSettingsProviderList() {
    if (!this.llmProviderList || !this.state.llmConfig) return;
    this.llmProviderList.innerHTML = '';

    const providers = this.state.llmConfig.providers || {};
    const activeKey = this.state.llmConfig.active_provider;

    Object.entries(providers).forEach(([key, prov]) => {
      const isSelected = key === this.state.selectedSettingsProvider;
      const isActive = key === activeKey;

      const item = document.createElement('div');
      item.className = `provider-nav-item ${isSelected ? 'active' : ''}`;
      item.innerHTML = `
        <div class="provider-nav-info">
          <span class="provider-nav-name">${this.escapeHtml(prov.name)}</span>
          <span class="provider-nav-type">${prov.type || 'engine'} • ${this.escapeHtml(prov.default_model)}</span>
        </div>
        ${isActive ? '<span class="provider-active-indicator">ACTIVE</span>' : ''}
      `;

      item.addEventListener('click', () => {
        this.state.selectedSettingsProvider = key;
        this.renderSettingsProviderList();
        this.selectSettingsProvider(key);
      });

      this.llmProviderList.appendChild(item);
    });
  }

  selectSettingsProvider(providerKey) {
    if (!this.state.llmConfig || !this.state.llmConfig.providers[providerKey]) return;
    const prov = this.state.llmConfig.providers[providerKey];
    this.state.selectedSettingsProvider = providerKey;

    this.currentProviderTitle.textContent = prov.name;
    this.currentProviderDesc.textContent = prov.description || '';
    this.inputLLMAPIBase.value = prov.api_base || '';
    this.inputLLMAPIKey.value = prov.api_key || '';
    if (this.inputLLMTimeout) {
      this.inputLLMTimeout.value = prov.timeout_seconds || 120;
    }
    this.sliderLLMTemperature.value = prov.temperature || 0.2;
    this.valLLMTemperature.textContent = prov.temperature || 0.2;

    // Populate model options
    this.selectLLMDefaultModel.innerHTML = '';
    const models = prov.models && prov.models.length ? prov.models : [prov.default_model];
    models.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m;
      opt.textContent = m;
      opt.selected = (m === prov.default_model);
      this.selectLLMDefaultModel.appendChild(opt);
    });

    // Custom model option
    const customOpt = document.createElement('option');
    customOpt.value = '__custom__';
    customOpt.textContent = '+ Custom Model Name...';
    this.selectLLMDefaultModel.appendChild(customOpt);

    this.inputLLMCustomModel.classList.add('hidden');
    this.inputLLMCustomModel.value = '';

    // Reset test pill
    this.testResultPill.classList.add('hidden');
  }

  async testCurrentLLMConnection() {
    const provKey = this.state.selectedSettingsProvider;
    let model = this.selectLLMDefaultModel.value;
    if (model === '__custom__') {
      model = this.inputLLMCustomModel.value.trim();
    }

    this.btnTestLLMConnection.disabled = true;
    this.btnTestLLMConnection.textContent = '⚡ Testing...';
    this.testResultPill.className = 'test-result-box';
    this.testResultPill.classList.remove('hidden', 'success', 'error');
    this.testResultIcon.textContent = '⏳';
    this.testResultMsg.textContent = 'Sending test ping...';

    try {
      // First persist temporary settings for accurate test
      await fetch('/api/llm/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_id: provKey,
          api_base: this.inputLLMAPIBase.value.trim(),
          api_key: this.inputLLMAPIKey.value.trim(),
          default_model: model
        })
      });

      const resp = await fetch('/api/llm/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider_id: provKey, model: model })
      });
      const data = await resp.json();

      this.btnTestLLMConnection.disabled = false;
      this.btnTestLLMConnection.innerHTML = '<span>⚡</span> Test Connection';

      if (data.success) {
        this.testResultPill.classList.add('success');
        this.testResultIcon.textContent = '✓';
        this.testResultMsg.textContent = data.message || `Connected in ${data.latency_ms}ms!`;
      } else {
        this.testResultPill.classList.add('error');
        this.testResultIcon.textContent = '✗';
        this.testResultMsg.textContent = data.message || 'Connection failed';
      }
    } catch (e) {
      this.btnTestLLMConnection.disabled = false;
      this.btnTestLLMConnection.innerHTML = '<span>⚡</span> Test Connection';
      this.testResultPill.classList.add('error');
      this.testResultIcon.textContent = '✗';
      this.testResultMsg.textContent = `Error: ${e.message}`;
    }
  }

  async setActiveLLMProvider() {
    const provKey = this.state.selectedSettingsProvider;
    let model = this.selectLLMDefaultModel.value;
    if (model === '__custom__') {
      model = this.inputLLMCustomModel.value.trim();
    }

    try {
      const resp = await fetch('/api/llm/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          active_provider: provKey,
          active_model: model,
          provider_id: provKey,
          api_base: this.inputLLMAPIBase.value.trim(),
          api_key: this.inputLLMAPIKey.value.trim(),
          default_model: model,
          temperature: parseFloat(this.sliderLLMTemperature.value),
          timeout_seconds: parseInt(this.inputLLMTimeout ? this.inputLLMTimeout.value : '120', 10) || 120
        })
      });
      const data = await resp.json();
      if (data.success) {
        alert(`✓ Set "${this.state.llmConfig.providers[provKey].name}" as the active default LLM!`);
        await this.loadLLMConfig();
      }
    } catch (e) {
      console.error('Failed to set active LLM:', e);
      alert('Failed to update active LLM.');
    }
  }

  async saveCurrentLLMConfig() {
    const provKey = this.state.selectedSettingsProvider;
    let model = this.selectLLMDefaultModel.value;
    if (model === '__custom__') {
      model = this.inputLLMCustomModel.value.trim();
    }

    this.btnSaveLLMConfig.disabled = true;
    this.btnSaveLLMConfig.textContent = 'Saving...';

    try {
      const resp = await fetch('/api/llm/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider_id: provKey,
          api_base: this.inputLLMAPIBase.value.trim(),
          api_key: this.inputLLMAPIKey.value.trim(),
          default_model: model,
          temperature: parseFloat(this.sliderLLMTemperature.value),
          timeout_seconds: parseInt(this.inputLLMTimeout ? this.inputLLMTimeout.value : '120', 10) || 120
        })
      });
      const data = await resp.json();
      this.btnSaveLLMConfig.disabled = false;
      this.btnSaveLLMConfig.innerHTML = '<span>💾</span> Save Provider Configuration';

      if (data.success) {
        alert(`✓ Settings for "${this.state.llmConfig.providers[provKey].name}" saved successfully!`);
        await this.loadLLMConfig();
      }
    } catch (e) {
      console.error('Failed to save LLM config:', e);
      this.btnSaveLLMConfig.disabled = false;
      this.btnSaveLLMConfig.innerHTML = '<span>💾</span> Save Provider Configuration';
      alert('Failed to save configuration.');
    }
  }

  // ─────────────────────────────────────────────────────────────
  // AI Fix Dialogue & Speakers Modal & Execution
  // ─────────────────────────────────────────────────────────────
  populateAIFixProviders() {
    if (!this.selectAIFixProvider || !this.state.llmConfig) return;
    this.selectAIFixProvider.innerHTML = '';

    const providers = this.state.llmConfig.providers || {};
    const activeKey = this.state.llmConfig.active_provider;

    Object.entries(providers).forEach(([key, prov]) => {
      const opt = document.createElement('option');
      opt.value = key;
      opt.textContent = `${prov.name} (${prov.type})`;
      opt.selected = (key === activeKey);
      this.selectAIFixProvider.appendChild(opt);
    });

    this.populateAIFixModels(this.selectAIFixProvider.value);
  }

  populateAIFixModels(providerKey) {
    if (!this.selectAIFixModel || !this.state.llmConfig) return;
    this.selectAIFixModel.innerHTML = '';
    const prov = this.state.llmConfig.providers[providerKey];
    if (!prov) return;

    const models = prov.models && prov.models.length ? prov.models : [prov.default_model];
    models.forEach(m => {
      const opt = document.createElement('option');
      opt.value = m;
      opt.textContent = m;
      opt.selected = (m === prov.default_model || m === this.state.llmConfig.active_model);
      this.selectAIFixModel.appendChild(opt);
    });
  }

  openAIFixModal() {
    if (!this.modalAIFixDialogue) return;
    this.populateAIFixProviders();
    const curChap = this.state.chaptersList.find(c => c.file === this.state.activeChapter);
    if (this.aiFixCurrentChapterName) {
      this.aiFixCurrentChapterName.textContent = curChap ? curChap.title : 'Current Chapter';
    }

    if (this.inputAIFixStoryLore) {
      const savedLore = localStorage.getItem(`novelcast_story_lore_${this.state.activeProject}`);
      if (savedLore !== null) {
        this.inputAIFixStoryLore.value = savedLore;
      }
    }

    this.aiFixProgressSection.classList.add('hidden');
    this.aiFixDiffList.innerHTML = '<div class="diff-placeholder">Click "Run AI Director" to begin...</div>';
    this.aiFixChangesCount.textContent = '0 corrections';
    this.btnSubmitAIFix.disabled = false;
    this.btnSubmitAIFix.innerHTML = '<span>🚀</span> Run AI Script Director';
    this.modalAIFixDialogue.classList.remove('hidden');
  }

  closeAIFixModal() {
    if (!this.modalAIFixDialogue) return;
    this.modalAIFixDialogue.classList.add('hidden');
  }

  async submitAIFix() {
    const scope = document.querySelector('input[name="aiFixScope"]:checked')?.value || 'chapter';
    const providerId = this.selectAIFixProvider.value;
    const model = this.selectAIFixModel.value;
    const refineSpeakers = this.chkAIFixSpeakers.checked;
    const refineInstructs = this.chkAIFixInstructs.checked;
    const insertTokens = this.chkAIFixTokens.checked;
    const storyLore = this.inputAIFixStoryLore ? this.inputAIFixStoryLore.value.trim() : '';

    if (this.inputAIFixStoryLore) {
      localStorage.setItem(`novelcast_story_lore_${this.state.activeProject}`, storyLore);
    }

    this.btnSubmitAIFix.disabled = true;
    this.btnSubmitAIFix.innerHTML = '<span>⏳</span> Directing Script with AI...';
    this.aiFixProgressSection.classList.remove('hidden');
    this.aiFixProgressBar.style.width = '20%';
    this.aiFixProgressPct.textContent = '20%';
    this.aiFixStatusText.textContent = `Connecting to ${providerId} (${model})...`;
    this.aiFixDiffList.innerHTML = '<div class="diff-placeholder">Analyzing narrative flow & attribution...</div>';

    if (scope === 'chapter') {
      try {
        const payload = {
          provider_id: providerId,
          model: model,
          story_lore: storyLore,
          refine_speakers: refineSpeakers,
          refine_instructs: refineInstructs,
          insert_audio_tokens: insertTokens,
          batch_size: 25
        };

        const resp = await fetch(`/api/scripts/${this.state.activeProject}/${this.state.activeChapter}/ai-fix`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        if (!resp.ok) {
          const errText = await resp.text();
          let errDetail = errText;
          try {
            const errJson = JSON.parse(errText);
            errDetail = errJson.detail || errJson.message || errText;
          } catch (_) {}
          this.btnSubmitAIFix.disabled = false;
          this.btnSubmitAIFix.innerHTML = '<span>🚀</span> Run AI Script Director';
          this.aiFixStatusText.textContent = `Error (${resp.status}): ${errDetail}`;
          return;
        }

        const data = await resp.json();
        this.btnSubmitAIFix.disabled = false;
        this.btnSubmitAIFix.innerHTML = '<span>🚀</span> Run AI Script Director';
        this.aiFixProgressBar.style.width = '100%';
        this.aiFixProgressPct.textContent = '100%';

        if (data.success) {
          this.aiFixStatusText.textContent = `✓ Directing Complete! Corrected ${data.total_fixed} line(s).`;
          this.aiFixChangesCount.textContent = `${data.total_fixed} corrections`;

          // Render Diff List
          if (data.diffs && data.diffs.length > 0) {
            this.aiFixDiffList.innerHTML = '';
            data.diffs.forEach(d => {
              const row = document.createElement('div');
              row.className = 'diff-item-row';
              
              let changeBadgeHtml = '';
              let changeContentHtml = '';

              if (d.speaker_changed) {
                changeBadgeHtml = '<span class="diff-badge speaker">🎙️ Speaker</span>';
                changeContentHtml = `
                  <span class="diff-chip-old">${this.escapeHtml(d.old_speaker)}</span>
                  <span class="diff-arrow">➔</span>
                  <span class="diff-chip-new">${this.escapeHtml(d.new_speaker)}</span>
                `;
              } else if (d.instruct_changed) {
                changeBadgeHtml = '<span class="diff-badge tone">🎭 Tone / Instruct</span>';
                changeContentHtml = `
                  <span class="diff-speaker-name">${this.escapeHtml(d.new_speaker)}</span>
                  <span class="diff-instruct-tag">${this.escapeHtml(d.new_instruct || 'neutral')}</span>
                `;
              } else if (d.token_changed) {
                changeBadgeHtml = '<span class="diff-badge token">⚡ Expression</span>';
                changeContentHtml = `<span class="diff-speaker-name">${this.escapeHtml(d.new_speaker)}</span>`;
              } else {
                changeBadgeHtml = '<span class="diff-badge speaker">✓ Updated</span>';
                changeContentHtml = `<span class="diff-chip-new">${this.escapeHtml(d.new_speaker)}</span>`;
              }

              row.innerHTML = `
                <span class="diff-num">#${d.id}</span>
                ${changeBadgeHtml}
                <div class="diff-change-body">${changeContentHtml}</div>
                <span class="diff-text-snippet" title="${this.escapeHtml(d.text)}">"${this.escapeHtml(d.text)}"</span>
              `;
              this.aiFixDiffList.appendChild(row);
            });
          } else {
            this.aiFixDiffList.innerHTML = '<div class="diff-placeholder" style="color: #34d399;">✓ All speakers and emotion prompts were already accurately attributed!</div>';
          }

          // Hot-reload current chapter script in Script Studio
          await this.loadChapterScript(this.state.activeChapter);
          await this.loadVoiceBank();
        } else {
          this.aiFixStatusText.textContent = `Error: ${data.detail || 'Failed to direct chapter'}`;
        }
      } catch (e) {
        console.error('AI Fix error:', e);
        this.btnSubmitAIFix.disabled = false;
        this.btnSubmitAIFix.innerHTML = '<span>🚀</span> Run AI Script Director';
        this.aiFixStatusText.textContent = `Directing failed: ${e.message}`;
      }
    } else {
      // Scope === 'all'
      try {
        const payload = {
          provider_id: providerId,
          model: model,
          story_lore: storyLore,
          refine_speakers: refineSpeakers,
          refine_instructs: refineInstructs,
          insert_audio_tokens: insertTokens,
          batch_size: 25
        };

        const resp = await fetch(`/api/scripts/${this.state.activeProject}/ai-fix-all`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });

        const data = await resp.json();
        if (data.success && data.job_id) {
          this.closeAIFixModal();
          this.startPipelineProgressPolling(data.job_id);
        } else {
          alert('Failed to start batch AI fix job.');
          this.btnSubmitAIFix.disabled = false;
          this.btnSubmitAIFix.innerHTML = '<span>🚀</span> Run AI Script Director';
        }
      } catch (e) {
        console.error('Batch AI Fix error:', e);
        this.btnSubmitAIFix.disabled = false;
        this.btnSubmitAIFix.innerHTML = '<span>🚀</span> Run AI Script Director';
        alert('Failed to start batch AI fix job.');
      }
    }
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
