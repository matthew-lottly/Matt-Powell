import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";


class MockMap {
	on(event: string, callback: () => void) {
		if (event === "load") {
			callback();
		}
		return this;
	}

	addControl() {
		return this;
	}

	addSource() {
		return this;
	}

	addLayer() {
		return this;
	}

	getSource() {
		return {
			setData: vi.fn(),
		};
	}

	remove() {
		return this;
	}
}


vi.mock("maplibre-gl", () => ({
	default: {
		Map: MockMap,
		NavigationControl: class NavigationControl {},
	},
	NavigationControl: class NavigationControl {},
}));
