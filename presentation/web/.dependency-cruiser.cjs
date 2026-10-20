module.exports = {
  forbidden: [
    { name: "no-cycles", severity: "error", from: {}, to: { circular: true } },
    {
      name: "resolved-imports",
      severity: "error",
      from: {},
      to: { couldNotResolve: true },
    },
    {
      name: "lib-is-independent",
      severity: "error",
      from: { path: "^src/lib/" },
      to: { path: "^src/(app|components)/" },
    },
    {
      name: "components-do-not-import-routes",
      severity: "error",
      from: { path: "^src/components/" },
      to: { path: "^src/app/" },
    },
    {
      name: "app-isolation",
      severity: "error",
      from: {},
      to: { path: "(^|/)\\.\\./|^/", pathNot: "node_modules" },
    },
  ],
  options: {
    doNotFollow: { path: "node_modules" },
    tsPreCompilationDeps: true,
    tsConfig: { fileName: "tsconfig.json" },
  },
};
