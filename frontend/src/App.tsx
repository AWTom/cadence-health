import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { UnitPage } from "./pages/UnitPage";

function Nav() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
      isActive
        ? "bg-blue-50 text-blue-700 font-semibold"
        : "text-slate-500 hover:text-slate-800 hover:bg-slate-100"
    }`;

  return (
    <nav className="h-14 flex items-center px-5 gap-3 flex-shrink-0 bg-white border-b border-slate-200 shadow-sm">
      <div className="flex items-center gap-2 mr-4">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" fill="#3b82f6" fillOpacity="0.15" stroke="#3b82f6" strokeWidth="1.8" strokeLinejoin="round"/>
        </svg>
        <span className="font-bold text-base tracking-tight text-slate-900">
          Fall<span className="text-blue-600">Guard</span>
        </span>
      </div>
      <NavLink to="/" end className={linkClass}>Unit Map</NavLink>
      <div className="flex-1" />
      <span className="text-xs text-slate-400 font-medium">UCSF Mission Bay · 7M</span>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col h-screen bg-slate-50">
        <Nav />
        <Routes>
          <Route path="/" element={<UnitPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
