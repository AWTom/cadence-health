import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { UnitPage } from "./pages/UnitPage";

function Nav() {
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `px-3 py-1.5 rounded text-sm font-medium transition-colors ${isActive ? "bg-blue-700 text-white" : "text-blue-100 hover:text-white hover:bg-blue-700/50"}`;

  return (
    <nav className="bg-blue-900 text-white h-14 flex items-center px-4 gap-4 flex-shrink-0">
      <span className="font-bold text-lg tracking-tight mr-4">FallGuard</span>
      <NavLink to="/" end className={linkClass}>Unit Map</NavLink>
      <div className="flex-1" />
      <span className="text-xs bg-amber-500 text-white px-2 py-1 rounded font-semibold">
        SYNTHETIC DATA — NOT FOR CLINICAL USE
      </span>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col h-screen bg-gray-50">
        <Nav />
        <Routes>
          <Route path="/" element={<UnitPage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
