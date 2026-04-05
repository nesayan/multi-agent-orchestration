require("dotenv").config();
const express = require("express");
const path = require("path");

const app = express();
const HOST = process.env.HOST || "0.0.0.0";
const PORT = process.env.PORT || 3000;
const BACKEND_URL = process.env.BACKEND_URL || "http://localhost:80";

// Serve static files from the "public" directory
app.use(express.static(path.join(__dirname, "public")));

// Config endpoint — serves backend URL to the browser
app.get("/config", (req, res) => {
  res.json({ backendUrl: BACKEND_URL });
});

// Routes
app.get("/", (req, res) => {
  res.sendFile(path.join(__dirname, "public", "index.html"));
});

app.listen(PORT, HOST, () => {
  console.log(`Server running at http://${HOST}:${PORT}`);
});
