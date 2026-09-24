import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router";
import { Shell, ToolsShell } from "./app";
import { CallsScreen } from "./screens/calls/calls";
import { CalendarScreen } from "./screens/calendar/calendar";
import { MetricsScreen } from "./screens/metrics/metrics";
import { NotFoundScreen } from "./screens/not-found";
import { TalkScreen } from "./screens/talk/talk";
import { SettingsScreen } from "./screens/settings/settings";
import "./styles/globals.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <Shell />,
    children: [
      { index: true, element: <Navigate to="/metrics" replace /> },
      { path: "dashboard", element: <Navigate to="/metrics" replace /> },
      { path: "calls", element: <CallsScreen /> },
      { path: "calls/:id", element: <CallsScreen /> },
      { path: "calendar", element: <CalendarScreen /> },
      { path: "metrics", element: <MetricsScreen /> },
      { path: "settings", element: <SettingsScreen /> },
      { path: "*", element: <NotFoundScreen /> },
    ],
  },
  {
    element: <ToolsShell />,
    children: [
      { path: "/talk", element: <TalkScreen /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
