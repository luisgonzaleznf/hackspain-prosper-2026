import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { createBrowserRouter, Navigate, RouterProvider } from "react-router";
import { Shell, ToolsShell } from "./app";
import { CallsScreen } from "./screens/calls/calls";
import { CalendarScreen } from "./screens/calendar/calendar";
import { CasesScreen } from "./screens/cases/cases";
import { MetricsScreen } from "./screens/metrics/metrics";
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
      { path: "*", element: <Navigate to="/metrics" replace /> },
    ],
  },
  {
    element: <ToolsShell />,
    children: [
      { path: "/cases", element: <CasesScreen /> },
      { path: "/cases/:caseId", element: <CasesScreen /> },
      { path: "/talk", element: <TalkScreen /> },
    ],
  },
]);

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
);
