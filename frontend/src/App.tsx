import ParticlesBackground from './components/ParticlesBackground'
import Header from './components/Header'
import PipelineCard from './components/cards/PipelineCard'
import HistoryCard from './components/cards/HistoryCard'
import PullsCard from './components/cards/PullsCard'
import CommitsCard from './components/cards/CommitsCard'
import VersionCard from './components/cards/VersionCard'
import TeamCard from './components/cards/TeamCard'
import './index.css'
import './App.css'

// Painel de uma tela só: cabeçalho + grade 3×2 com os 6 cards.
//   │ 1. Status da main │ 3. PRs abertos │ 5. Versão      │
//   │ 2. Últimos runs   │ 6. Commits     │ 4. Integrantes │
function App() {
  return (
    <>
      <ParticlesBackground />
      <main className="app">
        <Header />
        <div className="grid">
          <PipelineCard />
          <HistoryCard />
          <PullsCard />
          <CommitsCard />
          <VersionCard />
          <TeamCard />
        </div>
      </main>
    </>
  )
}

export default App
