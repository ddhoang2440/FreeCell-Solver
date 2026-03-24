import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import "./Home.css";

const API_URL = "http://localhost:5000/api";

const Home = () => {
  const navigate = useNavigate();
  const [seed, setSeed] = useState("1");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleNewGame = async () => {
    setLoading(true);
    setError("");

    try {
      const response = await axios.post(
        `${API_URL}/new-game`,
        {
          seed: parseInt(seed) || 1,
        },
        {
          withCredentials: true,
          headers: {
            "Content-Type": "application/json",
          },
        },
      );

      if (response.data.success) {
        navigate(`/game/${response.data.game_id}`);
      } else {
        setError("Failed to create game");
      }
    } catch (err) {
      setError("Error connecting to server");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSeedChange = (e) => {
    const value = e.target.value;
    if (value === "" || /^\d+$/.test(value)) {
      setSeed(value);
    }
  };

  return (
    <div className="home-container">
      <div className="home-header">
        <h1 className="home-title">FREE CELL SOLVER</h1>
        <div className="home-subtitle">Web Edition</div>
      </div>

      <div className="home-card">
        <h2 className="home-card-title">New Game</h2>

        <div className="input-group">
          <label htmlFor="seed-input" className="input-label">
            Seed Number:
          </label>
          <input
            id="seed-input"
            type="text"
            className="seed-input"
            value={seed}
            onChange={handleSeedChange}
            placeholder="Enter seed (1-99999)"
          />
        </div>

        {error && <div className="error-message">{error}</div>}

        <button
          className="new-game-button"
          onClick={handleNewGame}
          disabled={loading}
        >
          {loading ? <span className="loading-spinner"></span> : "START GAME"}
        </button>
      </div>
    </div>
  );
};

export default Home;
