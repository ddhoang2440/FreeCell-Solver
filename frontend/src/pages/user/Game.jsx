import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { io } from "socket.io-client";
import Card from "../../components/Card";

const API_URL = "http://localhost:5000/api";
const SOCKET_URL = "http://localhost:5000";

const Game = () => {
  const { gameId } = useParams();
  const navigate = useNavigate();
  const socketRef = useRef(null);
  const boardRef = useRef(null);

  const [gameState, setGameState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [statusMessage, setStatusMessage] = useState("Ready");
  const [selectedCards, setSelectedCards] = useState([]);

  const [dragging, setDragging] = useState(false);
  const [dragPosition, setDragPosition] = useState({ x: 0, y: 0 });
  const [dragSource, setDragSource] = useState(null);

  const [showSolverDialog, setShowSolverDialog] = useState(false);
  const [solverResults, setSolverResults] = useState(null);
  const [solving, setSolving] = useState(false);
  const [solverProgress, setSolverProgress] = useState({
    progress: 0,
    nodesExplored: 0,
    currentDepth: 0,
    bestHeuristic: 0,
    foundationCards: 0,
    freeCellsUsed: 0,
    explorationRate: 0,
    estimatedTime: "calculating...",
    solver: null,
  });

  const SCREEN_WIDTH = window.innerWidth > 1200 ? 1200 : window.innerWidth - 40;
  const SCREEN_HEIGHT = 700;
  const CARD_WIDTH = 80;
  const CARD_HEIGHT = 112;
  const CARD_PADDING = 10;

  const FREE_CELL_START_X = 20;
  const FREE_CELL_START_Y = 50;

  const FOUNDATION_START_X =
    SCREEN_WIDTH - 4 * (CARD_WIDTH + CARD_PADDING) - 20;
  const FOUNDATION_START_Y = 50;

  const CASCADE_START_X = 50;
  const CASCADE_START_Y = 220;
  const CASCADE_SPACING = Math.floor((SCREEN_WIDTH - 100 - CARD_WIDTH) / 7);

  useEffect(() => {
    const handleGlobalMouseUp = () => {
      if (dragging) {
        setDragging(false);
        setSelectedCards([]);
        setDragSource(null);
      }
    };

    window.addEventListener("mouseup", handleGlobalMouseUp);

    return () => {
      window.removeEventListener("mouseup", handleGlobalMouseUp);
    };
  }, [dragging]);

  useEffect(() => {
    socketRef.current = io(SOCKET_URL);

    socketRef.current.on("state_update", (data) => {
      if (data.game_id === gameId) {
        setGameState(data.state);
        if (data.last_move) {
          setStatusMessage("Move applied");
        }
      }
    });
    socketRef.current.on("solver_progress", (data) => {
      if (data.game_id === gameId) {
        console.log("solver_progress", data);
        setSolverProgress({
          progress: data.progress || 0,
          nodesExplored: data.nodes_explored || 0,
          currentDepth: data.current_depth || 0,
          bestHeuristic: data.best_heuristic || 0,
          foundationCards: data.foundation_cards || 0,
          freeCellsUsed: data.free_cells_used || 0,
          explorationRate: data.exploration_rate || 0,
          estimatedTime: data.estimated_remaining || "calculating...",
          solver: data.solver || solverProgress.solver,
        });

        // Update status message with progress
        if (data.progress < 100) {
          setStatusMessage(
            `${data.solver} solving... ${data.progress}% complete`,
          );
        }
      }
    });

    socketRef.current.on("solver_complete", (data) => {
      if (data.game_id === gameId) {
        setSolving(false);
        setSolverResults(data);
        setShowSolverDialog(true);
        setStatusMessage(`${data.solver} found solution!`);

        setSolverProgress({
          progress: 100,
          nodesExplored: data.results?.nodes_explored || 0,
          currentDepth: data.results?.solution_length || 0,
          bestHeuristic: 0,
          foundationCards: 52,
          freeCellsUsed: 4,
          explorationRate: 0,
          estimatedTime: "completed",
          solver: data.solver,
        });
      }
    });
    socketRef.current.on("solver_error", (data) => {
      if (data.game_id === gameId) {
        setSolving(false);
        setStatusMessage(`Solver error: ${data.error}`);

        setSolverProgress({
          progress: 0,
          nodesExplored: 0,
          currentDepth: 0,
          bestHeuristic: 0,
          foundationCards: 0,
          freeCellsUsed: 0,
          explorationRate: 0,
          estimatedTime: "error",
          solver: null,
        });
      }
    });

    loadGame();

    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
      }
    };
  }, [gameId, solverProgress.solver]);

  const loadGame = async () => {
    try {
      const response = await axios.get(`${API_URL}/game/${gameId}`, {
        withCredentials: true,
      });

      if (response.data.success) {
        setGameState(response.data.state);
        setStatusMessage("Game loaded");
      } else {
        setError("Game not found");
      }
    } catch (err) {
      setError("Failed to load game");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const makeMove = async (move) => {
    try {
      const response = await axios.post(
        `${API_URL}/game/${gameId}/move`,
        {
          move,
        },
        { withCredentials: true },
      );
      if (response.data.success) {
        console.log("game state", response.data.state);
        setGameState(response.data.state);
        if (response.data.is_goal) {
          setStatusMessage(" Congratulations! You won! ");
        }
      } else {
        setStatusMessage(" Invalid move!");
      }
    } catch (err) {
      setStatusMessage("Error making move");
      console.error(err);
    }
  };

  const handleNewGame = () => {
    navigate("/");
  };

  const handleRestart = async () => {
    try {
      const response = await axios.post(
        `${API_URL}/game/${gameId}/restart`,
        {},
        {
          withCredentials: true,
        },
      );

      if (response.data.success) {
        setGameState(response.data.state);
        setStatusMessage("Game restarted");
        setSelectedCards([]);
      }
    } catch (err) {
      setStatusMessage("Failed to restart");
    }
  };

  const handleUndo = async () => {
    try {
      const response = await axios.post(
        `${API_URL}/game/${gameId}/undo`,
        {},
        {
          withCredentials: true,
        },
      );

      if (response.data.success) {
        setGameState(response.data.state);
        setStatusMessage("Undo last move");
        setSelectedCards([]);
      }
    } catch (err) {
      setStatusMessage("No moves to undo");
    }
  };

  const handleSolve = async (solverName) => {
    if (solving) return;

    setSolving(true);
    setStatusMessage(` Running ${solverName} solver...`);

    setSolverProgress({
      progress: 0,
      nodesExplored: 0,
      currentDepth: 0,
      bestHeuristic: 0,
      foundationCards: 0,
      freeCellsUsed: 0,
      explorationRate: 0,
      estimatedTime: "calculating...",
      solver: solverName,
    });

    try {
      await axios.post(
        `${API_URL}/game/${gameId}/solve`,
        {
          solver: solverName,
        },
        { withCredentials: true },
      );
    } catch (err) {
      setSolving(false);
      setStatusMessage(" Failed to start solver");
    }
  };
  const getProgressColor = (progress) => {
    if (progress < 30) return "bg-red-500";
    if (progress < 60) return "bg-yellow-500";
    if (progress < 90) return "bg-blue-500";
    return "bg-green-500";
  };
  const getCascadeOffsetY = (cascadeLength) => {
    return Math.min(30, 400 / (cascadeLength + 1));
  };
  const getCardAtPosition = (x, y) => {
    if (!gameState) return null;

    for (let i = 0; i < 4; i++) {
      const rect = {
        x: FREE_CELL_START_X + i * (CARD_WIDTH + CARD_PADDING),
        y: FREE_CELL_START_Y,
        width: CARD_WIDTH,
        height: CARD_HEIGHT,
      };

      if (
        x >= rect.x &&
        x <= rect.x + rect.width &&
        y >= rect.y &&
        y <= rect.y + rect.height
      ) {
        const card = gameState.free_cells[i];
        return {
          type: "freecell",
          index: i,
          card: card,
        };
      }
    }

    const foundations = ["SPADES", "HEARTS", "CLUBS", "DIAMONDS"];
    for (let i = 0; i < foundations.length; i++) {
      const suit = foundations[i];
      const rect = {
        x: FOUNDATION_START_X + i * (CARD_WIDTH + CARD_PADDING),
        y: FOUNDATION_START_Y,
        width: CARD_WIDTH,
        height: CARD_HEIGHT,
      };

      if (
        x >= rect.x &&
        x <= rect.x + rect.width &&
        y >= rect.y &&
        y <= rect.y + rect.height
      ) {
        const pile = gameState.foundations[suit] || [];
        return {
          type: "foundation",
          index: i,
          suit,
          card: pile.length > 0 ? pile[pile.length - 1] : null,
          isEmpty: pile.length === 0,
        };
      }
    }

    for (let i = 0; i < 8; i++) {
      const cascadeX = CASCADE_START_X + i * CASCADE_SPACING;
      const cascade = gameState.cascades[i] || [];

      if (cascade.length === 0) {
        const rect = {
          x: cascadeX,
          y: CASCADE_START_Y,
          width: CARD_WIDTH,
          height: CARD_HEIGHT,
        };

        if (
          x >= rect.x &&
          x <= rect.x + rect.width &&
          y >= rect.y &&
          y <= rect.y + rect.height
        ) {
          return {
            type: "cascade_empty",
            index: i,
            card: null,
          };
        }
      } else {
        for (let j = cascade.length - 1; j >= 0; j--) {
          const offsetY = getCascadeOffsetY(cascade.length);
          const cardY = CASCADE_START_Y + j * offsetY;

          const rect = {
            x: cascadeX,
            y: cardY,
            width: CARD_WIDTH,
            height: CARD_HEIGHT,
          };

          if (
            x >= rect.x &&
            x <= rect.x + rect.width &&
            y >= rect.y &&
            y <= rect.y + rect.height
          ) {
            return {
              type: "cascade",
              index: i,
              row: j,
              card: cascade[j],
            };
          }
        }

        const currentOffsetY = getCascadeOffsetY(cascade.length);
        const lastCardY =
          CASCADE_START_Y + (cascade.length - 1) * currentOffsetY;
        const dropZoneY = lastCardY + CARD_HEIGHT;

        if (
          y >= dropZoneY &&
          y <= dropZoneY + 50 &&
          x >= cascadeX &&
          x <= cascadeX + CARD_WIDTH
        ) {
          return {
            type: "cascade_empty",
            index: i,
            card: null,
          };
        }
      }
    }
    return null;
  };
  const getSequenceFromCascade = (colIndex, startRow) => {
    const cascade = gameState?.cascades[colIndex];
    if (!cascade || startRow >= cascade.length) return [];

    const sequence = [cascade[startRow]];

    for (let i = startRow + 1; i < cascade.length; i++) {
      if (canPlaceOn(cascade[i], cascade[i - 1])) {
        sequence.push(cascade[i]);
      } else {
        break;
      }
    }

    return sequence;
  };

  const handleMouseDown = (e) => {
    if (solving) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const clicked = getCardAtPosition(x, y);

    if (!clicked || !clicked.card) return;

    // if (clicked.type === "foundation") return;

    console.log("Start drag:", clicked);

    if (clicked.type === "cascade") {
      const cascade = gameState.cascades[clicked.index];

      const sequence = getSequenceFromCascade(clicked.index, clicked.row);
      const maxSequenceLength = gameState?.max_sequence_length;
      if (sequence.length > 1) {
        if (sequence.length <= maxSequenceLength) {
          setSelectedCards(sequence);
          setDragSource({
            type: "cascade_sequence",
            index: clicked.index,
            row: clicked.row,
            length: sequence.length,
          });
          setStatusMessage(`Dragging sequence of ${sequence.length} cards`);
        } else {
          setStatusMessage(
            `Can not drag ${sequence.length} cards. Max: ${maxSequenceLength}`,
          );
        }
      } else if (clicked.row === cascade.length - 1) {
        setSelectedCards([clicked.card]);
        setDragSource({
          type: "cascade",
          index: clicked.index,
          row: clicked.row,
        });
        setStatusMessage(`Dragging 1 card`);
      } else {
        setStatusMessage("Cannot drag this card");
        return;
      }
    } else if (clicked.type === "freecell") {
      setSelectedCards([clicked.card]);
      setDragSource({
        type: "freecell",
        index: clicked.index,
      });
      setStatusMessage(`Dragging from freecell`);
    } else if (clicked.type === "foundation") {
      // Thêm drag từ foundation
      // Chỉ cho phép drag card cuối cùng của foundation pile
      const foundationPile = gameState.foundations[clicked.card.suit];
      if (
        foundationPile &&
        foundationPile.length > 0 &&
        foundationPile[foundationPile.length - 1].rank === clicked.card.rank &&
        foundationPile[foundationPile.length - 1].suit === clicked.card.suit
      ) {
        setSelectedCards([clicked.card]);
        setDragSource({
          type: "foundation",
          index: clicked.index, // index là suit index
          suit: clicked.card.suit,
        });
        setStatusMessage(
          `Dragging from foundation: ${clicked.card.rank} of ${clicked.card.suit}`,
        );
      } else {
        setStatusMessage("Cannot drag this card from foundation");
        return;
      }
    }

    const cardRect = getCardRect(clicked);
    if (cardRect) {
      setDragPosition({
        x: x - cardRect.x,
        y: y - cardRect.y,
      });
    } else {
      setDragPosition({ x: CARD_WIDTH / 2, y: CARD_HEIGHT / 2 });
    }

    setDragging(true);
  };
  // const getCardRect = (clicked) => {
  //   if (!clicked || !clicked.card) return null;

  //   if (clicked.type === "cascade") {
  //     const cascade = gameState?.cascades[clicked.index] || [];
  //     const offsetY = Math.min(30, Math.floor(400 / (cascade.length + 1)));
  //     return {
  //       x: CASCADE_START_X + clicked.index * CASCADE_SPACING,
  //       y: CASCADE_START_Y + clicked.row * offsetY,
  //       width: CARD_WIDTH,
  //       height: CARD_HEIGHT,
  //     };
  //   } else if (clicked.type === "freecell") {
  //     return {
  //       x: FREE_CELL_START_X + clicked.index * (CARD_WIDTH + CARD_PADDING),
  //       y: FREE_CELL_START_Y,
  //       width: CARD_WIDTH,
  //       height: CARD_HEIGHT,
  //     };
  //   }
  //   return null;
  // };
  const getCardRect = (clicked) => {
    if (!clicked || !clicked.card) return null;

    if (clicked.type === "cascade") {
      const cascade = gameState?.cascades[clicked.index] || [];
      const offsetY = Math.min(30, Math.floor(400 / (cascade.length + 1)));
      return {
        x: CASCADE_START_X + clicked.index * CASCADE_SPACING,
        y: CASCADE_START_Y + clicked.row * offsetY,
        width: CARD_WIDTH,
        height: CARD_HEIGHT,
      };
    } else if (clicked.type === "freecell") {
      return {
        x: FREE_CELL_START_X + clicked.index * (CARD_WIDTH + CARD_PADDING),
        y: FREE_CELL_START_Y,
        width: CARD_WIDTH,
        height: CARD_HEIGHT,
      };
    } else if (clicked.type === "foundation") {
      // Thêm foundation rect
      const suitIndex = ["SPADES", "HEARTS", "CLUBS", "DIAMONDS"].indexOf(
        clicked.suit,
      );
      return {
        x: FOUNDATION_START_X + suitIndex * (CARD_WIDTH + CARD_PADDING),
        y: FOUNDATION_START_Y,
        width: CARD_WIDTH,
        height: CARD_HEIGHT,
      };
    }
    return null;
  };
  const handleMouseMove = (e) => {
    if (!dragging || !boardRef.current) return;

    const rect = boardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    setDragPosition({ x, y });
  };
  const canPlaceOn = (card, belowCard) => {
    const cardColor =
      card.suit === "HEARTS" || card.suit === "DIAMONDS" ? "red" : "black";
    const belowColor =
      belowCard.suit === "HEARTS" || belowCard.suit === "DIAMONDS"
        ? "red"
        : "black";

    return cardColor !== belowColor && card.rank === belowCard.rank - 1;
  };

  const handleMouseUp = (e) => {
    if (!dragging || !dragSource || !boardRef.current) return;

    const rect = boardRef.current.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    const target = getCardAtPosition(x, y);
    console.log("target", target);
    console.log("dragSource", dragSource);
    console.log("selectedCards", selectedCards);

    if (target && selectedCards.length > 0) {
      let move = null;

      // Xử lý drag từ foundation
      if (dragSource.type === "foundation") {
        if (selectedCards.length === 1) {
          if (target.type === "cascade" || target.type === "cascade_empty") {
            // Foundation to cascade
            move = ["foundation_to_cascade", dragSource.suit, target.index];
            console.log(`Moving from foundation to cascade ${target.index}`);
          } else if (target.type === "freecell") {
            // Foundation to freecell
            if (!gameState?.free_cells[target.index]) {
              move = ["foundation_to_freecell", dragSource.suit, target.index];
              console.log(`Moving from foundation to freecell ${target.index}`);
            } else {
              setStatusMessage("❌ Free cell is not empty");
            }
          } else {
            setStatusMessage(
              "❌ Can only drop foundation cards to cascade or freecell",
            );
          }
        } else {
          setStatusMessage("❌ Can only drag single card from foundation");
        }
      }
      // Xử lý drag từ cascade_sequence
      else if (dragSource.type === "cascade_sequence") {
        if (target.type === "cascade" || target.type === "cascade_empty") {
          if (dragSource.index !== target.index) {
            const destCascade = gameState?.cascades[target.index];
            const firstCard = selectedCards[0];
            console.log("destCascade", destCascade);
            const canPlace =
              !destCascade?.length ||
              canPlaceOn(firstCard, destCascade[destCascade.length - 1]);

            const maxSequenceLength = gameState?.max_sequence_length;
            console.log("maxSequenceLength", maxSequenceLength);
            console.log("canPlace", canPlace);
            if (selectedCards.length <= maxSequenceLength && canPlace) {
              move = [
                "cascade_to_cascade_sequence",
                dragSource.index,
                target.index,
                selectedCards.length,
              ];
              console.log(`Moving sequence of ${selectedCards.length} cards`);
            } else {
              setStatusMessage(
                `Cannot move ${selectedCards.length} cards! Max: ${maxSequenceLength}`,
              );
            }
          }
        } else {
          setStatusMessage("Sequence can only be dropped to cascade");
        }
      }
      // Xử lý drag từ cascade
      else if (dragSource.type === "cascade") {
        if (selectedCards.length === 1) {
          if (target.type === "cascade" || target.type === "cascade_empty") {
            if (dragSource.index !== target.index) {
              move = ["cascade_to_cascade", dragSource.index, target.index];
            }
          } else if (target.type === "freecell") {
            if (!gameState?.free_cells[target.index]) {
              move = ["cascade_to_freecell", dragSource.index, target.index];
            }
          } else if (target.type === "foundation") {
            move = ["cascade_to_foundation", dragSource.index];
          }
        }
      }
      // Xử lý drag từ freecell
      else if (dragSource.type === "freecell") {
        if (target.type === "cascade" || target.type === "cascade_empty") {
          move = ["freecell_to_cascade", dragSource.index, target.index];
        } else if (target.type === "freecell") {
          if (
            dragSource.index !== target.index &&
            !gameState?.free_cells[target.index]
          ) {
            move = ["freecell_to_freecell", dragSource.index, target.index];
          }
        } else if (target.type === "foundation") {
          move = ["freecell_to_foundation", dragSource.index];
        }
      }

      if (move) {
        console.log("Sending move:", move);
        makeMove(move);
      } else {
        setStatusMessage("❌ Invalid move");
      }
    } else {
      setStatusMessage("❌ Invalid drop target");
    }

    setDragging(false);
    setSelectedCards([]);
    setDragSource(null);
  };
  // const handleMouseUp = (e) => {
  //   if (!dragging || !dragSource || !boardRef.current) return;

  //   const rect = boardRef.current.getBoundingClientRect();
  //   const x = e.clientX - rect.left;
  //   const y = e.clientY - rect.top;

  //   const target = getCardAtPosition(x, y);
  //   console.log("target", target);
  //   console.log("dragSource", dragSource);
  //   console.log("selectedCards", selectedCards);

  //   if (target && selectedCards.length > 0) {
  //     let move = null;

  //     if (dragSource.type === "cascade_sequence") {
  //       if (target.type === "cascade" || target.type === "cascade_empty") {
  //         if (dragSource.index !== target.index) {
  //           const destCascade = gameState?.cascades[target.index];
  //           const firstCard = selectedCards[0];
  //           console.log("destCascade", destCascade);
  //           const canPlace =
  //             !destCascade?.length ||
  //             canPlaceOn(firstCard, destCascade[destCascade.length - 1]);

  //           const maxSequenceLength = gameState?.max_sequence_length;
  //           console.log("maxSequenceLength", maxSequenceLength);
  //           console.log("canPlace", canPlace);
  //           if (selectedCards.length <= maxSequenceLength && canPlace) {
  //             move = [
  //               "cascade_to_cascade_sequence",
  //               dragSource.index,
  //               target.index,
  //               selectedCards.length,
  //             ];
  //             console.log(`Moving sequence of ${selectedCards.length} cards`);
  //           } else {
  //             setStatusMessage(
  //               `Cannot move ${selectedCards.length} cards! Max: ${maxSequenceLength}`,
  //             );
  //           }
  //         }
  //       } else {
  //         setStatusMessage("Sequence can only be dropped to cascade");
  //       }
  //     } else if (dragSource.type === "cascade") {
  //       if (selectedCards.length === 1) {
  //         if (target.type === "cascade" || target.type === "cascade_empty") {
  //           if (dragSource.index !== target.index) {
  //             move = ["cascade_to_cascade", dragSource.index, target.index];
  //           }
  //         } else if (target.type === "freecell") {
  //           if (!gameState?.free_cells[target.index]) {
  //             move = ["cascade_to_freecell", dragSource.index, target.index];
  //           }
  //         } else if (target.type === "foundation") {
  //           move = ["cascade_to_foundation", dragSource.index];
  //         }
  //       }
  //     } else if (dragSource.type === "freecell") {
  //       if (target.type === "cascade" || target.type === "cascade_empty") {
  //         move = ["freecell_to_cascade", dragSource.index, target.index];
  //       } else if (target.type === "freecell") {
  //         if (
  //           dragSource.index !== target.index &&
  //           !gameState?.free_cells[target.index]
  //         ) {
  //           move = ["freecell_to_freecell", dragSource.index, target.index];
  //         }
  //       } else if (target.type === "foundation") {
  //         move = ["freecell_to_foundation", dragSource.index];
  //       }
  //     }

  //     if (move) {
  //       console.log("Sending move:", move);
  //       makeMove(move);
  //     } else {
  //       setStatusMessage("❌ Invalid move");
  //     }
  //   } else {
  //     setStatusMessage("❌ Invalid drop target");
  //   }

  //   setDragging(false);
  //   setSelectedCards([]);
  //   setDragSource(null);
  // };
  const renderCard = (card, isDragged = false) => {
    if (!card) return null;

    return (
      <Card
        key={`${card.suit}-${card.rank}`}
        suit={card.suit}
        rank={card.rank}
        width={CARD_WIDTH}
        height={CARD_HEIGHT}
        isDragged={isDragged}
      />
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-linear-to-br from-green-900 to-green-700">
        <div className="w-16 h-16 border-4 border-yellow-500/30 border-t-yellow-500 rounded-full animate-spin"></div>
        <div className="mt-5 text-yellow-500 text-lg font-bold">
          Loading game...
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-linear-to-br from-green-900 to-green-700 text-white">
        <h2 className="text-4xl text-red-500 mb-5">Error</h2>
        <p className="text-lg mb-8 opacity-90">{error}</p>
        <button
          onClick={handleNewGame}
          className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-semibold"
        >
          Back to Home
        </button>
      </div>
    );
  }

  const gameContainerStyle = {
    width: SCREEN_WIDTH,
    height: SCREEN_HEIGHT,
    margin: "0 auto",
    position: "relative",
  };

  return (
    <div className="min-h-screen bg-linear-to-br from-green-900 to-green-700 relative font-sans">
      <div className="bg-green-950/95 px-8 py-4 border-b-4 border-yellow-500 shadow-lg relative z-10">
        <h1 className="text-yellow-500 text-4xl mb-3 text-center font-bold drop-shadow-[2px_2px_0_black] tracking-wider">
          FREE CELL SOLVER
        </h1>

        <div className="flex items-center gap-2 flex-wrap justify-center">
          <button
            onClick={handleNewGame}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors font-semibold shadow-md"
          >
            New Game
          </button>
          <button
            onClick={handleRestart}
            className="px-4 py-2 bg-orange-600 text-white rounded-md hover:bg-orange-700 transition-colors font-semibold shadow-md"
          >
            Restart
          </button>
          <button
            onClick={handleUndo}
            className="px-4 py-2 bg-gray-600 text-white rounded-md hover:bg-gray-700 transition-colors font-semibold shadow-md"
          >
            Undo
          </button>

          <div className="bg-gray-800 text-yellow-500 px-4 py-2 rounded-full font-bold text-sm border border-yellow-500 shadow-inner">
            Seed: {gameState?.seed || "N/A"}
          </div>

          <div className="flex gap-1 ml-4">
            <button
              onClick={() => handleSolve("BFS")}
              disabled={solving}
              className={`px-3 py-1.5 rounded-md font-semibold text-sm transition-colors ${
                solving ? "opacity-50 cursor-not-allowed" : ""
              } bg-purple-600 text-white hover:bg-purple-700`}
            >
              BFS
            </button>
            <button
              onClick={() => handleSolve("DFS")}
              disabled={solving}
              className={`px-3 py-1.5 rounded-md font-semibold text-sm transition-colors ${
                solving ? "opacity-50 cursor-not-allowed" : ""
              } bg-orange-600 text-white hover:bg-orange-700`}
            >
              DFS
            </button>
            <button
              onClick={() => handleSolve("UCS")}
              disabled={solving}
              className={`px-3 py-1.5 rounded-md font-semibold text-sm transition-colors ${
                solving ? "opacity-50 cursor-not-allowed" : ""
              } bg-green-600 text-white hover:bg-green-700`}
            >
              UCS
            </button>
            <button
              onClick={() => handleSolve("A*")}
              disabled={solving}
              className={`px-3 py-1.5 rounded-md font-semibold text-sm transition-colors ${
                solving ? "opacity-50 cursor-not-allowed" : ""
              } bg-red-600 text-white hover:bg-red-700`}
            >
              A*
            </button>
          </div>
        </div>
      </div>
      {solving && (
        <div className="container mx-auto px-4 py-4">
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-xl p-4 border border-gray-700">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="animate-spin h-4 w-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
                <span className="text-sm font-medium text-gray-300">
                  {solverProgress.solver} Solver
                </span>
              </div>
              <span className="text-sm text-gray-400">
                {solverProgress.progress}%
              </span>
            </div>

            <div className="h-2 bg-gray-700 rounded-full overflow-hidden mb-4">
              <div
                className={`h-full transition-all duration-300 ease-out ${getProgressColor(solverProgress.progress)}`}
                style={{ width: `${solverProgress.progress}%` }}
              ></div>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="bg-gray-700/30 rounded-lg p-2">
                <div className="text-gray-400 text-xs">Nodes Explored</div>
                <div className="text-white font-medium">
                  {solverProgress.nodesExplored.toLocaleString()}
                </div>
              </div>
              <div className="bg-gray-700/30 rounded-lg p-2">
                <div className="text-gray-400 text-xs">Current Depth</div>
                <div className="text-white font-medium">
                  {solverProgress.currentDepth}
                </div>
              </div>
              <div className="bg-gray-700/30 rounded-lg p-2">
                <div className="text-gray-400 text-xs">Foundation Cards</div>
                <div className="text-white font-medium">
                  {solverProgress.foundationCards}/52
                </div>
              </div>
              <div className="bg-gray-700/30 rounded-lg p-2">
                <div className="text-gray-400 text-xs">Est. Remaining</div>
                <div className="text-white font-medium">
                  {solverProgress.estimatedTime}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4 mt-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Exploration Rate:</span>
                <span className="text-gray-300">
                  {solverProgress.explorationRate} nodes/s
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Best Heuristic:</span>
                <span className="text-gray-300">
                  {solverProgress.bestHeuristic}
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-gray-400">Free Cells:</span>
                <span className="text-gray-300">
                  {solverProgress.freeCellsUsed}/4
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
      <div
        ref={boardRef}
        className="relative cursor-default select-none"
        style={gameContainerStyle}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={() => {
          setDragging(false);
          setSelectedCards([]);
          setDragSource(null);
        }}
      >
        <div
          className="absolute"
          style={{ left: FREE_CELL_START_X, top: FREE_CELL_START_Y - 30 }}
        >
          <div className="text-yellow-500 text-sm font-bold mb-1 uppercase tracking-wider drop-shadow-[1px_1px_0_black]">
            Free Cells
          </div>
        </div>
        {[0, 1, 2, 3].map((i) => {
          const card = gameState?.free_cells[i];
          const isEmpty = !card;
          const x = FREE_CELL_START_X + i * (CARD_WIDTH + CARD_PADDING);
          return (
            <div
              key={`freecell-${i}`}
              className={`absolute w-20 h-28 border-2 border-yellow-500 rounded-lg bg-black/30 shadow-inner
      ${!isEmpty && !dragging ? "hover:border-yellow-300 hover:shadow-lg hover:scale-105 cursor-grab" : ""}
      ${isEmpty ? "border-dashed border-yellow-500/50" : ""}`}
              style={{ left: x, top: FREE_CELL_START_Y }}
              data-type="freecell"
              data-index={i}
            >
              {card ? (
                <div className="w-full h-full flex items-center justify-center">
                  {renderCard(card)}
                </div>
              ) : (
                <div className="w-full h-full flex items-center justify-center text-yellow-500/30 text-2xl">
                  📌
                </div>
              )}
            </div>
          );
        })}
        <div
          className="absolute"
          style={{ left: FOUNDATION_START_X, top: FOUNDATION_START_Y - 30 }}
        >
          <div className="text-yellow-500 text-sm font-bold mb-1 uppercase tracking-wider drop-shadow-[1px_1px_0_black]">
            Foundations
          </div>
        </div>
        {["SPADES", "HEARTS", "CLUBS", "DIAMONDS"].map((suit, i) => {
          const pile = gameState?.foundations[suit] || [];
          const isEmpty = pile.length === 0;
          const x = FOUNDATION_START_X + i * (CARD_WIDTH + CARD_PADDING);
          return (
            <div
              key={`foundation-${suit}`}
              className={`absolute w-20 h-28 border-2 border-yellow-500 rounded-lg bg-black/30 shadow-inner
      ${isEmpty ? "border-dashed border-yellow-500/50" : ""}`}
              style={{ left: x, top: FOUNDATION_START_Y }}
              data-type="foundation"
              data-index={i}
              data-suit={suit}
            >
              {!isEmpty ? (
                <div className="w-full h-full flex items-center justify-center">
                  {renderCard(pile[pile.length - 1])}
                </div>
              ) : (
                <div className="w-full h-full flex items-center justify-center text-5xl text-yellow-500/30 font-bold">
                  {suit === "SPADES" && "♠"}
                  {suit === "HEARTS" && "♥"}
                  {suit === "CLUBS" && "♣"}
                  {suit === "DIAMONDS" && "♦"}
                </div>
              )}
            </div>
          );
        })}

        {gameState?.cascades.map((cascade, colIndex) => {
          const isEmpty = cascade.length === 0;
          const canDragSequence = cascade.length > 1;
          const x = CASCADE_START_X + colIndex * CASCADE_SPACING;

          return (
            <div
              key={`cascade-col-${colIndex}`}
              className="absolute w-20"
              style={{ left: x, top: CASCADE_START_Y - 35 }}
              data-type="cascade-column"
              data-index={colIndex}
            >
              <div className="text-center text-yellow-500 font-bold text-sm mb-2 drop-shadow-[1px_1px_0_black] bg-black/30 py-1 px-2 rounded-full border border-yellow-500">
                C{colIndex + 1}
              </div>

              <div
                className={`relative w-full rounded transition-all ${isEmpty ? "h-28 border-2 border-dashed border-yellow-500/30" : ""}`}
                data-type="cascade"
                data-index={colIndex}
                data-empty={isEmpty}
              >
                {cascade.map((card, rowIndex) => {
                  const offsetY = getCascadeOffsetY(cascade.length);
                  const y = rowIndex * offsetY;
                  const isLastCard = rowIndex === cascade.length - 1;
                  const isDragged =
                    dragging &&
                    dragSource?.type === "cascade" &&
                    dragSource?.index === colIndex &&
                    dragSource?.row === rowIndex;
                  const isInDraggedSequence =
                    dragging &&
                    dragSource?.type === "cascade" &&
                    dragSource?.index === colIndex &&
                    rowIndex >= dragSource?.row;

                  return (
                    <div
                      key={`card-${colIndex}-${rowIndex}`}
                      className={`absolute left-0 transition-all ${!dragging && !isLastCard ? "hover:z-20" : ""} ${isInDraggedSequence && !isDragged ? "opacity-50" : ""}`}
                      style={{
                        top: y,
                        width: CARD_WIDTH,
                        height: CARD_HEIGHT,
                        zIndex: isDragged ? 30 : isLastCard ? 20 : rowIndex + 1,
                        cursor:
                          !dragging && (isLastCard || canDragSequence)
                            ? "grab"
                            : "default",
                      }}
                      data-type="cascade-card"
                      data-col={colIndex}
                      data-row={rowIndex}
                      data-card={JSON.stringify(card)}
                    >
                      <div
                        className={`relative w-full h-full ${!dragging && (isLastCard || canDragSequence) ? "hover:scale-105 hover:-translate-y-1 hover:shadow-xl" : ""}`}
                      >
                        <Card
                          suit={card.suit}
                          rank={card.rank}
                          width={CARD_WIDTH}
                          height={CARD_HEIGHT}
                          isDragged={isDragged}
                        />
                      </div>
                    </div>
                  );
                })}
                {isEmpty && !dragging && (
                  <div className="absolute inset-0 flex items-center justify-center text-yellow-500/30 text-4xl">
                    empty
                  </div>
                )}
              </div>
            </div>
          );
        })}
        {dragging && selectedCards.length > 0 && (
          <>
            {selectedCards.map((card, i) => (
              <div
                key={`drag-${i}`}
                className="absolute pointer-events-none z-50 transition-transform"
                style={{
                  left: dragPosition.x - CARD_WIDTH / 2,
                  top: dragPosition.y - CARD_HEIGHT / 2 + i * 15,
                  transform: `rotate(${i * 2}deg) scale(1.05)`,
                  filter: "drop-shadow(0 20px 25px rgba(0, 0, 0, 0.5))",
                  opacity: 0.95,
                }}
              >
                <Card
                  suit={card.suit}
                  rank={card.rank}
                  width={CARD_WIDTH}
                  height={CARD_HEIGHT}
                />

                {i === 0 && selectedCards.length > 1 && (
                  <div className="absolute -top-3 -right-3 bg-yellow-500 text-black text-xs font-bold rounded-full w-6 h-6 flex items-center justify-center border-2 border-black">
                    {selectedCards.length}
                  </div>
                )}
              </div>
            ))}
            <div className="absolute pointer-events-none inset-0">
              {dragSource && (
                <div className="fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-black/80 text-yellow-500 px-4 py-2 rounded-full border border-yellow-500 text-sm">
                  Đang kéo {selectedCards.length} card(s)
                </div>
              )}
            </div>
          </>
        )}

        {dragging && dragSource && (
          <div className="absolute inset-0 pointer-events-none">
            {[0, 1, 2, 3].map((i) => {
              if (!gameState?.free_cells[i] && dragSource.type !== "freecell") {
                return (
                  <div
                    key={`drop-highlight-freecell-${i}`}
                    className="absolute w-20 h-28 border-4 border-green-400 rounded-lg animate-pulse"
                    style={{
                      left: FREE_CELL_START_X + i * (CARD_WIDTH + CARD_PADDING),
                      top: FREE_CELL_START_Y,
                      boxShadow: "0 0 20px rgba(74, 222, 128, 0.5)",
                    }}
                  />
                );
              }
              return null;
            })}

            {gameState?.cascades.map((cascade, colIndex) => {
              const canDrop = dragSource.index !== colIndex;
              if (!canDrop) return null;

              const lastCardY =
                cascade.length > 0
                  ? CASCADE_START_Y +
                    (cascade.length - 1) * getCascadeOffsetY(cascade.length)
                  : CASCADE_START_Y;

              return (
                <div
                  key={`drop-highlight-cascade-${colIndex}`}
                  className="absolute border-4 border-green-400 rounded-lg animate-pulse"
                  style={{
                    left: CASCADE_START_X + colIndex * CASCADE_SPACING,
                    top: lastCardY,
                    width: CARD_WIDTH,
                    height: CARD_HEIGHT,
                    boxShadow: "0 0 20px rgba(74, 222, 128, 0.5)",
                  }}
                />
              );
            })}
          </div>
        )}
      </div>

      {statusMessage && (
        <div className="fixed bottom-8 left-1/2 -translate-x-1/2 bg-black/90 text-yellow-500 px-8 py-3 rounded-full text-base font-bold border-2 border-yellow-500 shadow-2xl backdrop-blur-sm animate-[slideUp_0.3s_ease] z-100">
          {statusMessage}
        </div>
      )}

      {showSolverDialog && solverResults && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-2xl p-6 max-w-md w-full mx-4 border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold text-white">Solver Results</h3>
              <button
                onClick={() => setShowSolverDialog(false)}
                className="p-1 hover:bg-gray-700 rounded-lg transition-colors"
              >
                <svg
                  className="w-6 h-6 text-gray-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M6 18L18 6M6 6l12 12"
                  ></path>
                </svg>
              </button>
            </div>

            <div className="space-y-4">
              <div className="bg-gray-700/50 rounded-lg p-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <div className="text-sm text-gray-400">Algorithm</div>
                    <div className="text-lg font-semibold text-white">
                      {solverResults.solver}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-400">Solution Found</div>
                    <div
                      className={`text-lg font-semibold ${solverResults.results?.solution_found ? "text-green-400" : "text-red-400"}`}
                    >
                      {solverResults.results?.solution_found ? "✓ Yes" : "✗ No"}
                    </div>
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-700/30 rounded-lg p-3">
                  <div className="text-sm text-gray-400">Nodes Explored</div>
                  <div className="text-xl font-bold text-white">
                    {solverResults.results?.nodes_explored?.toLocaleString()}
                  </div>
                </div>
                <div className="bg-gray-700/30 rounded-lg p-3">
                  <div className="text-sm text-gray-400">Time Taken</div>
                  <div className="text-xl font-bold text-white">
                    {solverResults.results?.time_taken?.toFixed(2)}s
                  </div>
                </div>
                <div className="bg-gray-700/30 rounded-lg p-3">
                  <div className="text-sm text-gray-400">Memory Used</div>
                  <div className="text-xl font-bold text-white">
                    {solverResults.results?.memory_used?.toFixed(2)} MB
                  </div>
                </div>
                <div className="bg-gray-700/30 rounded-lg p-3">
                  <div className="text-sm text-gray-400">Solution Length</div>
                  <div className="text-xl font-bold text-white">
                    {solverResults.results?.solution_length}
                  </div>
                </div>
              </div>

              {solverResults.results?.solution_found && (
                <button
                  onClick={() => {
                    setShowSolverDialog(false);
                  }}
                  className="w-full px-4 py-3 bg-linear-to-r from-green-500 to-green-600 hover:from-green-600 hover:to-green-700 rounded-lg font-semibold transition-all"
                >
                  Apply Solution
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Game;
