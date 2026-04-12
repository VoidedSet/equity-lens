declare module "d3-force-3d" {
  export function forceCollide(radius?: number): {
    radius(r: number): this;
    strength(s: number): this;
    iterations(n: number): this;
    (alpha: number): void;
    initialize(nodes: unknown[]): void;
  };
  export function forceManyBody(): {
    strength(s: number): this;
    theta(t: number): this;
    distanceMin(d: number): this;
    distanceMax(d: number): this;
    (alpha: number): void;
    initialize(nodes: unknown[]): void;
  };
}
