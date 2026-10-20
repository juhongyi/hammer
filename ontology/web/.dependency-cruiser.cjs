module.exports = {
  forbidden: [
    { name: "no-cycles", severity: "error", from: {}, to: { circular: true } },
    {
      name: "no-unresolved",
      severity: "error",
      from: {},
      to: { couldNotResolve: true },
    },
    {
      name: "product-isolation",
      severity: "error",
      from: { path: "^src/" },
      to: { path: "^\\.\\./" },
    },
    ...["app", "components", "hooks", "api", "lib"].flatMap(
      (layer, index, layers) =>
        layers.slice(0, index).map((upper) => ({
          name: `${layer}-must-not-import-${upper}`,
          severity: "error",
          from: { path: `^src/${layer}/` },
          to: { path: `^src/${upper}/` },
        })),
    ),
    {
      name: "ui-is-independent",
      severity: "error",
      from: { path: "^src/components/ui/" },
      to: { path: "^src/(hooks|api)/|^src/components/(?!ui/)" },
    },
    {
      name: "api-and-lib-are-react-free",
      severity: "error",
      from: { path: "^src/(api|lib)/" },
      to: { path: "(^|/)node_modules/(react|react-dom)(/|$)" },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    tsConfig: { fileName: "tsconfig.json" },
    tsPreCompilationDeps: true,
    enhancedResolveOptions: {
      exportsFields: ["exports"],
      conditionNames: ["import", "require", "node", "default"],
    },
  },
};
