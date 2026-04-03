import "./App.css";
import { Route, Routes } from "react-router-dom";
import Home from "./pages/user/Home";
import LayoutClient from "./layouts/user/LayoutClient";
import { Toaster } from "react-hot-toast";
import NotFound404 from "./components/NotFound404";
import Game from "./pages/user/Game";
import Statistics from "./pages/user/Statistics";
function App() {
  return (
    <>
      <Toaster />
      <Routes>
        <Route element={<LayoutClient />}>
          <Route path="/" element={<Home />} />
          <Route path="/game/:gameId" element={<Game />} />
          <Route path="/statistics" element={<Statistics />} />
        </Route>
        <Route path="*" element={<NotFound404 />} />
      </Routes>
    </>
  );
}

export default App;
