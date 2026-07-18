import { describe, it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import ThemeProvider from "@/context/ThemeContext";

// Mock react-leaflet to avoid JSDOM canvas issues
vi.mock("react-leaflet", () => ({
  MapContainer: ({ children }) => <div data-testid="map-container">{children}</div>,
  TileLayer: () => null,
  Marker: () => null,
  Tooltip: () => null,
  useMap: () => ({
    eachLayer: vi.fn(),
    removeLayer: vi.fn(),
    setView: vi.fn(),
    getZoom: () => 5,
  }),
}));

vi.mock("leaflet", () => ({
  default: {
    Icon: { Default: { prototype: {}, mergeOptions: vi.fn() } },
    divIcon: vi.fn(() => ({})),
    marker: vi.fn(() => ({
      addTo: vi.fn().mockReturnThis(),
      on: vi.fn().mockReturnThis(),
      bindTooltip: vi.fn().mockReturnThis(),
      setIcon: vi.fn(),
      getLatLng: vi.fn(() => ({ lat: 0, lng: 0 })),
      remove: vi.fn(),
    })),
    tileLayer: vi.fn(() => ({ addTo: vi.fn() })),
    TileLayer: class {},
  },
}));

import LandingPage from "@/pages/LandingPage";
import Predictor from "@/pages/Predictor";
import Navbar from "@/components/layout/Navbar";

const MOCK_STATIONS = [
  {
    id: "1",
    name: "Test Station A",
    city: "Delhi",
    state: "Delhi",
    aqi: 120,
    category: "Moderate",
    pm25: 60,
    no2: 30,
    temp: 28,
    humidity: 65,
    wind_speed: 10,
    latitude: 28.6,
    longitude: 77.2,
  },
  {
    id: "2",
    name: "Test Station B",
    city: "Mumbai",
    state: "Maharashtra",
    aqi: 80,
    category: "Satisfactory",
    pm25: 35,
    no2: 20,
    temp: 30,
    humidity: 70,
    wind_speed: 12,
    latitude: 19.0,
    longitude: 72.8,
  },
];

function Wrapper({ children }) {
  return (
    <ThemeProvider>
      <MemoryRouter>
        {children}
      </MemoryRouter>
    </ThemeProvider>
  );
}

describe("Smoke tests: key components mount without throwing", () => {
  it("LandingPage renders with empty stations array", () => {
    expect(() =>
      render(<LandingPage stations={[]} />, { wrapper: Wrapper })
    ).not.toThrow();
  });

  it("LandingPage renders with populated stations array", () => {
    expect(() =>
      render(<LandingPage stations={MOCK_STATIONS} />, { wrapper: Wrapper })
    ).not.toThrow();
  });

  it("Predictor renders with a station list", () => {
    expect(() =>
      render(<Predictor stations={MOCK_STATIONS} />, { wrapper: Wrapper })
    ).not.toThrow();
  });

  it("Predictor renders empty-state when no stations", () => {
    expect(() =>
      render(<Predictor stations={[]} />, { wrapper: Wrapper })
    ).not.toThrow();
  });

  it("Navbar renders without throwing", () => {
    expect(() =>
      render(
        <Wrapper>
          <Navbar alerts={[]} showAlertPanel={false} onToggleAlerts={() => {}} />
        </Wrapper>
      )
    ).not.toThrow();
  });

  it("Navbar contains no FontAwesome <i> elements", () => {
    const { container } = render(
      <Wrapper>
        <Navbar alerts={[]} showAlertPanel={false} onToggleAlerts={() => {}} />
      </Wrapper>
    );
    const faIcons = container.querySelectorAll('i[class^="fa"]');
    expect(faIcons.length).toBe(0);
  });
});
