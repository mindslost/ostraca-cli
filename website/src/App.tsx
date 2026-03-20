import React, { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { 
  Terminal, 
  Search, 
  FolderGit2, 
  Layers, 
  Database, 
  Archive, 
  Cpu, 
  Copy, 
  Check, 
  Github, 
  ExternalLink,
  ChevronRight,
  Zap,
  Lock,
  PenLine,
  Power
} from 'lucide-react';

// --- Components ---

const Navbar = ({ isOled, toggleOled }: { isOled: boolean, toggleOled: () => void }) => (
  <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-charcoal/80 backdrop-blur-md px-6 py-4 flex justify-between items-center">
    <div className="flex items-center gap-2">
      <Terminal className="text-terminal-green w-6 h-6" />
      <span className="font-bold tracking-tighter text-xl">nexus.cli</span>
    </div>
    <div className="flex items-center gap-6">
      <a href="#features" className="text-sm hover:text-terminal-green transition-colors hidden md:block">Features</a>
      <a href="#demo" className="text-sm hover:text-terminal-green transition-colors hidden md:block">Demo</a>
      <a href="https://github.com/mindslost/nexus-cli/blob/main/docs/documentation.md" target="_blank" rel="noreferrer" className="text-sm hover:text-terminal-green transition-colors hidden md:block">Docs</a>
      <button 
        onClick={toggleOled}
        className={`p-2 rounded-full transition-all ${isOled ? 'bg-terminal-green text-black' : 'bg-white/5 text-white hover:bg-white/10'}`}
        title={isOled ? "Switch to Charcoal" : "Switch to OLED Black"}
      >
        <Power className="w-4 h-4" />
      </button>
      <a href="https://github.com/mindslost/nexus-cli" target="_blank" rel="noreferrer" className="bg-white text-black px-4 py-1.5 rounded text-sm font-bold hover:bg-terminal-green transition-colors flex items-center gap-2">
        <Github className="w-4 h-4" />
        GitHub
      </a>
    </div>
  </nav>
);

const Hero = () => {
  return (
    <section className="relative pt-32 pb-20 px-6 overflow-hidden min-h-screen flex flex-col justify-center items-center text-center">
      <div className="absolute inset-0 terminal-grid opacity-20 pointer-events-none" />
      <div className="scanline pointer-events-none" />
      
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="z-10 max-w-4xl"
      >
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-terminal-green/10 border border-terminal-green/20 text-terminal-green text-xs mb-6">
          <Zap className="w-3 h-3" />
          <span>v1.2.0 is now live with MCP support</span>
        </div>
        
        <h1 className="text-5xl md:text-7xl font-bold tracking-tighter mb-6 leading-tight">
          nexus cli <span className="text-terminal-green">"the future of notes"</span>
        </h1>
        
        <p className="text-xl md:text-2xl text-white/60 mb-10 max-w-2xl mx-auto leading-relaxed">
          A PARA-method PKB that speaks the language of both humans and AI.
        </p>
        
        <div className="flex flex-col md:flex-row items-center justify-center gap-4">
          <a href="#docs" className="px-8 py-3.5 rounded bg-terminal-green text-black hover:bg-white hover:text-black transition-all font-bold">
            View Quickstart
          </a>
        </div>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.4, duration: 0.8 }}
        className="mt-20 w-full max-w-5xl aspect-video bg-black rounded-lg border border-white/10 shadow-2xl overflow-hidden relative group"
      >
        <div className="absolute top-0 left-0 right-0 h-8 bg-white/5 border-b border-white/10 flex items-center px-4 gap-2">
          <div className="w-3 h-3 rounded-full bg-red-500/50" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
          <div className="w-3 h-3 rounded-full bg-green-500/50" />
          <div className="ml-4 text-[10px] text-white/30 uppercase tracking-widest">nexus-cli — bash — 80x24</div>
        </div>
        
        <div className="p-8 text-left font-mono text-[10px] md:text-xs leading-relaxed h-full overflow-hidden">
          <div className="flex gap-2 mb-2">
            <span className="text-terminal-green">$</span>
            <TypingText text="nexus list" delay={50} />
          </div>
          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1.5 }}
            className="text-white/80"
          >
            <div>Nexus</div>
            <div>├── <span className="text-terminal-cyan">Projects</span></div>
            <div>│   ├── <span className="text-white/40">ciwiXGri</span> | <span className="text-terminal-green">Project: Nexus CLI Development</span> <span className="text-white/40">(python, cli, sqlite)</span></div>
            <div>│   └── <span className="text-white/40">RP2nm8hq</span> | <span className="text-terminal-green">Project: Website Redesign</span> <span className="text-white/40">(web, redesign, frontend)</span></div>
            <div>├── <span className="text-terminal-cyan">Areas</span></div>
            <div>│   ├── <span className="text-white/40">CRuZG8MV</span> | <span className="text-terminal-green">Area: Personal Health</span> <span className="text-white/40">(health, fitness, habits)</span></div>
            <div>│   └── <span className="text-white/40">R78u3NqR</span> | <span className="text-terminal-green">Working with NVIM and Markdown</span> <span className="text-white/40">(nvim, markdown, how-to)</span></div>
            <div>├── <span className="text-terminal-cyan">Resources</span></div>
            <div>│   ├── <span className="text-white/40">HNm5D2Ng</span> | <span className="text-terminal-green">Collision Test Note</span></div>
            <div>│   ├── <span className="text-white/40">GMKH7g9Z</span> | <span className="text-terminal-green">Resource: Python Design Patterns</span> <span className="text-white/40">(python, patterns, coding)</span></div>
            <div>│   └── <span className="text-white/40">7WBkRLHN</span> | <span className="text-terminal-green">Short ID Test Note</span></div>
            <div>└── <span className="text-terminal-cyan">Archives</span></div>
            <div>    └── <span className="text-white/40">eMUiCjH9</span> | <span className="text-terminal-green">Archive: Budget 2024</span> <span className="text-white/40">(finance, budget, historical)</span></div>
          </motion.div>

          <div className="flex gap-2 mt-6 mb-2">
            <span className="text-terminal-green">$</span>
            <TypingText text='nexus search "markdown"' delay={50} startDelay={3000} />
          </div>

          <motion.div 
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 4.5 }}
            className="text-white/80"
          >
            <div className="text-center italic text-white/40 mb-2">Search Results for 'markdown'</div>
            <div className="border border-white/20 rounded overflow-hidden text-[9px] md:text-[10px]">
              <div className="grid grid-cols-[60px_1fr_80px_2fr_120px] bg-white/5 border-b border-white/20 font-bold">
                <div className="px-2 py-1 border-r border-white/20">ID</div>
                <div className="px-2 py-1 border-r border-white/20">Title</div>
                <div className="px-2 py-1 border-r border-white/20">Category</div>
                <div className="px-2 py-1 border-r border-white/20">Snippet</div>
                <div className="px-2 py-1">Last Updated</div>
              </div>
              <div className="grid grid-cols-[60px_1fr_80px_2fr_120px] border-b border-white/10">
                <div className="px-2 py-2 border-r border-white/20 text-white/40">R78u3NqR</div>
                <div className="px-2 py-2 border-r border-white/20 text-terminal-green">Working with NVIM and Markdown</div>
                <div className="px-2 py-2 border-r border-white/20 text-purple-400">Area</div>
                <div className="px-2 py-2 border-r border-white/20 text-white/60 leading-tight">
                  --- title: "Working with NVIM and <span className="text-yellow-400">Markdown</span>" para: Area tags: ["nvim", "<span className="text-yellow-400">markdown</span>", "how-to"] --- # How Best to Use NVIM with <span className="text-yellow-400">Markdown</span>...
                </div>
                <div className="px-2 py-2 text-terminal-green">2026-03-19 23:06:43</div>
              </div>
              <div className="grid grid-cols-[60px_1fr_80px_2fr_120px]">
                <div className="px-2 py-2 border-r border-white/20 text-white/40">ciwiXGri</div>
                <div className="px-2 py-2 border-r border-white/20 text-terminal-green">Project: Nexus CLI Development</div>
                <div className="px-2 py-2 border-r border-white/20 text-purple-400">Project</div>
                <div className="px-2 py-2 border-r border-white/20 text-white/60 leading-tight">
                  ...Project tags: --- ## Nexus CLI Development ## TODO Items - [ ] Export function (file structure and <span className="text-yellow-400">markdown</span> files)
                </div>
                <div className="px-2 py-2 text-terminal-green">2026-03-17 00:11:03</div>
              </div>
            </div>
          </motion.div>
        </div>
      </motion.div>
    </section>
  );
};

const TypingText = ({ text, delay, startDelay = 0 }: { text: string, delay: number, startDelay?: number }) => {
  const [currentText, setCurrentText] = useState("");
  const [started, setStarted] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setStarted(true), startDelay);
    return () => clearTimeout(timer);
  }, [startDelay]);

  useEffect(() => {
    if (!started) return;
    if (currentText.length < text.length) {
      const timeout = setTimeout(() => {
        setCurrentText(text.slice(0, currentText.length + 1));
      }, delay);
      return () => clearTimeout(timeout);
    }
  }, [currentText, text, delay, started]);

  return <span>{currentText}<span className="animate-pulse">_</span></span>;
};

const FeatureGrid = () => {
  const features = [
    {
      title: "Projects",
      icon: <FolderGit2 className="w-6 h-6" />,
      desc: "Active efforts with a deadline. Track milestones and daily logs.",
      command: 'nexus add "<title>" --para Project'
    },
    {
      title: "Areas",
      icon: <Layers className="w-6 h-6" />,
      desc: "Ongoing responsibilities. Health, Finance, Career, Hobbies.",
      command: 'nexus add "<title>" --para Area'
    },
    {
      title: "Resources",
      icon: <Database className="w-6 h-6" />,
      desc: "Topics of interest. Research, snippets, and reference material.",
      command: 'nexus add "<title>" --para Resource'
    },
    {
      title: "Archives",
      icon: <Archive className="w-6 h-6" />,
      desc: "Completed projects or inactive areas. Kept for future reference.",
      command: 'nexus add "<title>" --para Archive'
    }
  ];

  return (
    <section id="features" className="py-24 px-6 bg-black/30">
      <div className="max-w-6xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-5xl font-bold mb-4 tracking-tight">The PARA Advantage</h2>
          <p className="text-white/50 max-w-2xl mx-auto">Nexus natively enforces the PARA organization method, ensuring every piece of information has a clear home and a defined lifecycle.</p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((f, i) => (
            <motion.div 
              key={i}
              whileHover={{ y: -5 }}
              className="p-8 rounded-xl bg-white/5 border border-white/10 hover:border-terminal-green/50 transition-all group"
            >
              <div className="w-12 h-12 rounded bg-terminal-green/10 flex items-center justify-center text-terminal-green mb-6 group-hover:scale-110 transition-transform">
                {f.icon}
              </div>
              <h3 className="text-xl font-bold mb-3">{f.title}</h3>
              <p className="text-white/50 text-sm leading-relaxed mb-6">{f.desc}</p>
              <div className="text-[10px] font-mono text-terminal-green bg-terminal-green/5 px-2 py-1 rounded inline-block">
                {f.command}
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
};

const AiMcpSection = () => {
  return (
    <section className="py-24 px-6">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <div className="inline-flex items-center gap-2 text-terminal-cyan text-sm font-bold mb-4">
              <Cpu className="w-4 h-4" />
              AI-NATIVE CONTEXT
            </div>
            <h2 className="text-4xl md:text-5xl font-bold mb-6 tracking-tight leading-tight">
              Bridge the Gap Between You and Your AI.
            </h2>
            <p className="text-white/60 text-lg mb-8 leading-relaxed">
              Nexus isn't just for you; it's for your agents. With a built-in Model Context Protocol (MCP) server, 
              Nexus serves as a high-fidelity context provider for LLMs, allowing them to autonomously search and retrieve your notes.
            </p>
            
            <ul className="space-y-4">
              {[
                { icon: <Search className="w-5 h-5" />, text: "Sub-millisecond FTS5 search" },
                { icon: <Terminal className="w-5 h-5" />, text: "Machine-optimized XML output" },
                { icon: <Lock className="w-5 h-5" />, text: "Local-first, privacy-focused" }
              ].map((item, i) => (
                <li key={i} className="flex items-center gap-3 text-white/80">
                  <div className="text-terminal-green">{item.icon}</div>
                  {item.text}
                </li>
              ))}
            </ul>
          </div>
          
          <div className="space-y-4">
            <div className="bg-black rounded-lg border border-white/10 overflow-hidden">
              <div className="px-4 py-2 bg-white/5 border-b border-white/10 text-[10px] uppercase tracking-widest text-white/40">Human Readable</div>
              <pre className="p-4 text-xs md:text-sm text-terminal-green overflow-x-auto">
{`$ nexus search "sqlite"
                    Search Results for 'sqlite'
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓
┃ ID       ┃ Title                    ┃ Category ┃ Snippet             ┃ Last Updated        ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩
│ m3n4o5p6 │ SQLite FTS5 Documentation│ Resource │ ...how to optimize  │ 2026-03-19 14:30:05 │
│          │                          │          │ sqlite search...    │                     │
├──────────┼──────────────────────────┼──────────┼─────────────────────┼─────────────────────┤
│ e5f6g7h8 │ Nexus CLI Launch         │ Project  │ ...powered by a     │ 2026-03-19 10:15:22 │
│          │                          │          │ sqlite backend...   │                     │
└──────────┴──────────────────────────┴──────────┴─────────────────────┴─────────────────────┘`}
              </pre>
            </div>
            
            <div className="bg-black rounded-lg border border-white/10 overflow-hidden">
              <div className="px-4 py-2 bg-white/5 border-b border-white/10 text-[10px] uppercase tracking-widest text-white/40">AI Context (XML)</div>
              <pre className="p-4 text-xs md:text-sm text-terminal-cyan overflow-x-auto">
{`<context_provider name="nexus">
  <search_result query="mcp">
    <note id="1" path="resources/mcp_guide.md">
      <content>The Model Context Protocol (MCP) is...</content>
    </note>
    <note id="2" path="projects/nexus_cli.md">
      <content>Implemented MCP server in v1.2.0...</content>
    </note>
  </search_result>
</context_provider>`}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

const QuickStart = () => {
  const [activeTab, setActiveTab] = useState(0);
  const tabs = [
    {
      label: "1. Installation",
      code: `# Install Nexus CLI directly from the source
git clone https://github.com/mindslost/nexus-cli.git
cd nexus-cli
pip install -e .`
    },
    {
      label: "2. Configuration",
      code: `# Set your preferred terminal editor (nvim, vim, nano)
export EDITOR=nvim  # Add this to your .zshrc or .bashrc

# Enable shell autocompletion for note IDs and Titles
nexus --install-completion zsh  # or bash/fish`
    },
    {
      label: "3. PARA Workflow",
      code: `# Capture a New Note
nexus add "New Feature Ideas" --para Project
# Note 'New Feature Ideas' added successfully.

# Browse Your Knowledge Base
nexus list
Nexus
├── Projects
│   ├── ciwiXGri | Project: Nexus CLI Development (python, cli, sqlite)
│   └── RP2nm8hq | Project: Website Redesign (web, redesign, frontend)
├── Areas
│   ├── CRuZG8MV | Area: Personal Health (health, fitness, habits)
│   └── R78u3NqR | Working with NVIM and Markdown (nvim, markdown, how-to)
├── Resources
│   ├── HNm5D2Ng | Collision Test Note
│   ├── GMKH7g9Z | Resource: Python Design Patterns (python, patterns, coding)
│   └── 7WBkRLHN | Short ID Test Note
└── Archives
    └── eMUiCjH9 | Archive: Budget 2024 (finance, budget, historical)`
    },
    {
      label: "4. AI Integration",
      code: `# Start the MCP Server
nexus mcp-start
* FastMCP server 'Nexus' starting...
* Transport: stdio
* Tools registered: search_nexus_notes, get_project_context
* Server is running and waiting for AI agent requests. (Press Ctrl+C to stop)`
    }
  ];

  return (
    <section id="docs" className="py-24 px-6 bg-black/30">
      <div className="max-w-4xl mx-auto">
        <h2 className="text-3xl md:text-5xl font-bold mb-12 text-center tracking-tight">Quick Start Guide</h2>
        
        <div className="bg-black rounded-xl border border-white/10 overflow-hidden shadow-2xl">
          <div className="flex border-b border-white/10 overflow-x-auto no-scrollbar">
            {tabs.map((tab, i) => (
              <button
                key={i}
                onClick={() => setActiveTab(i)}
                className={`px-6 py-4 text-xs md:text-sm font-bold transition-all whitespace-nowrap ${activeTab === i ? 'text-terminal-green border-b-2 border-terminal-green bg-white/5' : 'text-white/40 hover:text-white/60'}`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="p-8 min-h-[300px] flex flex-col justify-center">
            <motion.div
              key={activeTab}
              initial={{ opacity: 0, x: 10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3 }}
            >
              <pre className="text-sm md:text-base text-white/80 overflow-x-auto leading-relaxed font-mono">
                {tabs[activeTab].code}
              </pre>
            </motion.div>
          </div>
        </div>
        
        <div className="mt-12 flex flex-col items-center gap-8">
          <a 
            href="https://github.com/mindslost/nexus-cli/blob/main/docs/quickstart.md" 
            target="_blank" 
            rel="noreferrer"
            className="inline-flex items-center gap-2 text-terminal-green hover:text-white transition-colors font-bold group"
          >
            View Full Quick Start Guide
            <ExternalLink className="w-4 h-4 group-hover:translate-x-1 group-hover:-translate-y-1 transition-transform" />
          </a>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-sm text-white/40">
            <div className="flex items-start gap-3">
              <div className="mt-1 text-terminal-green"><PenLine className="w-4 h-4" /></div>
              <p>Nexus uses your native <code className="text-white/60">$EDITOR</code> for zero-friction capture in standard Markdown.</p>
            </div>
            <div className="flex items-start gap-3">
              <div className="mt-1 text-terminal-cyan"><Cpu className="w-4 h-4" /></div>
              <p>The MCP server allows LLMs like Claude to autonomously search and retrieve your notes with high fidelity.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

const CommandSimulator = () => {
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<{ type: 'in' | 'out', content: React.ReactNode }[]>([
    { type: 'out', content: "Nexus CLI v1.2.0 — Type 'help' for commands." }
  ]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [history]);

  const handleCommand = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const newHistory = [...history, { type: 'in' as const, content: input }];
    
    let output: React.ReactNode = "";
    const cmd = input.toLowerCase().trim();

    if (cmd === 'help' || cmd === 'nexus --help') {
      output = (
        <div className="space-y-1 text-[10px] md:text-xs">
          <div>Usage: nexus [OPTIONS] COMMAND [ARGS]...</div>
          <div className="my-2">Nexus CLI - A terminal-based personal knowledge base enforcing the PARA method.</div>
          <div className="text-terminal-cyan">Options:</div>
          <div>  --install-completion [bash|zsh|fish|powershell|pwsh]</div>
          <div>  --show-completion [bash|zsh|fish|powershell|pwsh]</div>
          <div>  --help                          Show this message and exit.</div>
          <div className="text-terminal-cyan mt-2">Commands:</div>
          <div>  add        Create a new note with a title and category.</div>
          <div>  delete     Permanently delete a note.</div>
          <div>  edit       Edit an existing note's content and metadata.</div>
          <div>  list       List notes organized in a PARA directory tree.</div>
          <div>  mcp-start  Start the FastMCP server for AI agent integration.</div>
          <div>  move       Quickly move a note to a different PARA category.</div>
          <div>  open       Open a note in read-only mode for viewing.</div>
          <div>  search     Search notes using Full-Text Search.</div>
        </div>
      );
    } else if (cmd === 'nexus list' || cmd === 'list') {
      output = (
        <div className="space-y-0 text-[10px] md:text-xs font-mono">
          <div>Nexus</div>
          <div>├── <span className="text-terminal-cyan">Projects</span></div>
          <div>│   ├── <span className="text-white/40">ciwiXGri</span> | <span className="text-terminal-green">Project: Nexus CLI Development</span> <span className="text-white/40">(python, cli, sqlite)</span></div>
          <div>│   └── <span className="text-white/40">RP2nm8hq</span> | <span className="text-terminal-green">Project: Website Redesign</span> <span className="text-white/40">(web, redesign, frontend)</span></div>
          <div>├── <span className="text-terminal-cyan">Areas</span></div>
          <div>│   ├── <span className="text-white/40">CRuZG8MV</span> | <span className="text-terminal-green">Area: Personal Health</span> <span className="text-white/40">(health, fitness, habits)</span></div>
          <div>│   └── <span className="text-white/40">R78u3NqR</span> | <span className="text-terminal-green">Working with NVIM and Markdown</span> <span className="text-white/40">(nvim, markdown, how-to)</span></div>
          <div>├── <span className="text-terminal-cyan">Resources</span></div>
          <div>│   ├── <span className="text-white/40">HNm5D2Ng</span> | <span className="text-terminal-green">Collision Test Note</span></div>
          <div>│   ├── <span className="text-white/40">GMKH7g9Z</span> | <span className="text-terminal-green">Resource: Python Design Patterns</span> <span className="text-white/40">(python, patterns, coding)</span></div>
          <div>│   └── <span className="text-white/40">7WBkRLHN</span> | <span className="text-terminal-green">Short ID Test Note</span></div>
          <div>└── <span className="text-terminal-cyan">Archives</span></div>
          <div>    └── <span className="text-white/40">eMUiCjH9</span> | <span className="text-terminal-green">Archive: Budget 2024</span> <span className="text-white/40">(finance, budget, historical)</span></div>
        </div>
      );
    } else if (cmd.startsWith('nexus search') || cmd.startsWith('search') || cmd.startsWith('nexus cli') || cmd.startsWith('cli')) {
      output = (
        <div className="space-y-0 text-[8px] md:text-[10px] font-mono leading-tight">
          <div className="text-center">Search Results for 'sqlite'</div>
          <div>┏━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┓</div>
          <div>┃ ID       ┃ Title                    ┃ Category ┃ Snippet             ┃ Last Updated        ┃</div>
          <div>┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━┩</div>
          <div>│ m3n4o5p6 │ SQLite FTS5 Documentation│ Resource │ ...how to optimize  │ 2026-03-19 14:30:05 │</div>
          <div>│          │                          │          │ sqlite search...    │                     │</div>
          <div>├──────────┼──────────────────────────┼──────────┼─────────────────────┼─────────────────────┤</div>
          <div>│ e5f6g7h8 │ Nexus CLI Launch         │ Project  │ ...powered by a     │ 2026-03-19 10:15:22 │</div>
          <div>│          │                          │          │ sqlite backend...   │                     │</div>
          <div>└──────────┴──────────────────────────┴──────────┴─────────────────────┴─────────────────────┘</div>
        </div>
      );
    } else if (cmd.startsWith('nexus add') || cmd.startsWith('add')) {
      output = <div className="text-terminal-green">Note 'New Feature Ideas' added successfully.</div>;
    } else if (cmd.startsWith('nexus mcp-start') || cmd.startsWith('mcp-start')) {
      output = (
        <div className="space-y-1">
          <div>* FastMCP server 'Nexus' starting...</div>
          <div>* Transport: stdio</div>
          <div>* Tools registered: search_nexus_notes, get_project_context</div>
          <div>* Server is running and waiting for AI agent requests. (Press Ctrl+C to stop)</div>
        </div>
      );
    } else {
      output = <div className="text-red-400">Command not found: {cmd}</div>;
    }

    setHistory([...newHistory, { type: 'out', content: output }]);
    setInput("");
  };

  return (
    <section id="demo" className="py-24 px-6">
      <div className="max-w-3xl mx-auto">
        <div className="text-center mb-12">
          <h2 className="text-2xl font-bold mb-2">Try it yourself</h2>
          <p className="text-white/40 text-sm">Interactive terminal simulator</p>
        </div>
        
        <div className="bg-oled-black rounded-lg border border-white/10 shadow-2xl overflow-hidden">
          <div className="h-8 bg-white/5 border-b border-white/10 flex items-center px-4">
            <div className="text-[10px] text-white/30 uppercase tracking-widest">nexus-simulator — interactive</div>
          </div>
          
          <div 
            ref={scrollRef}
            className="p-6 h-64 overflow-y-auto font-mono text-sm space-y-2 scrollbar-hide"
          >
            {history.map((h, i) => (
              <div key={i} className="flex gap-2">
                {h.type === 'in' ? <span className="text-terminal-green">$</span> : null}
                <div className={h.type === 'in' ? 'text-white' : 'text-white/60'}>
                  {h.content}
                </div>
              </div>
            ))}
          </div>
          
          <form onSubmit={handleCommand} className="p-4 bg-white/5 border-t border-white/10 flex gap-2">
            <span className="text-terminal-green font-mono">$</span>
            <input 
              type="text" 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="type 'help'..."
              className="bg-transparent border-none outline-none flex-1 font-mono text-sm text-white placeholder:text-white/20"
            />
          </form>
        </div>
      </div>
    </section>
  );
};

const Footer = () => (
  <footer className="py-12 px-6 border-t border-white/5 bg-black">
    <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-8">
      <div className="flex flex-col items-center md:items-start gap-4">
        <div className="flex items-center gap-2">
          <Terminal className="text-terminal-green w-5 h-5" />
          <span className="font-bold tracking-tighter">nexus.cli</span>
        </div>
        <p className="text-white/30 text-xs text-center md:text-left">
          Built with Typer & Rich. Apache License 2.0. © 2026 Jason Lysinger.
        </p>
      </div>
      
      <div className="flex gap-8">
        <a href="https://github.com/mindslost/nexus-cli" className="text-white/40 hover:text-white transition-colors"><Github className="w-5 h-5" /></a>
        <a href="https://github.com/mindslost/nexus-cli/blob/main/docs/documentation.md" target="_blank" rel="noreferrer" className="text-white/40 hover:text-white transition-colors text-sm font-bold">Documentation</a>
        <a href="#" className="text-white/40 hover:text-white transition-colors text-sm font-bold">Changelog</a>
      </div>
      
      <div className="flex items-center gap-4">
        <a 
          href="https://github.com/fastapi/typer" 
          target="_blank" 
          rel="noreferrer" 
          className="px-3 py-1 rounded border border-white/10 text-[10px] font-bold text-white/40 hover:text-terminal-green hover:border-terminal-green transition-colors"
        >
          BUILT WITH TYPER
        </a>
        <a 
          href="https://github.com/Textualize/rich" 
          target="_blank" 
          rel="noreferrer" 
          className="px-3 py-1 rounded border border-white/10 text-[10px] font-bold text-white/40 hover:text-terminal-green hover:border-terminal-green transition-colors"
        >
          RICH OUTPUT
        </a>
      </div>
    </div>
  </footer>
);

// --- Main App ---

export default function App() {
  const [isOled, setIsOled] = useState(false);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  const toggleOled = () => {
    setIsOled(!isOled);
  };

  return (
    <div className={`min-h-screen transition-colors duration-500 ${isOled ? 'bg-oled-black' : 'bg-charcoal'}`}>
      <Navbar isOled={isOled} toggleOled={toggleOled} />
      
      <main>
        <Hero />
        <FeatureGrid />
        <AiMcpSection />
        <CommandSimulator />
        <QuickStart />
      </main>
      
      <Footer />
    </div>
  );
}
