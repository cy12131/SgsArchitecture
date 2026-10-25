-- Contract-only pseudo implementation; it is not an end-to-end tested package.
local pkg = Runtime.registerPackage { id = "org.sgs.example.runtime_bridge", version = "0.1.0" }

pkg:registerGameMode {
  id = "bridge_demo",
  min_players = 2,
  max_players = 2,
  ui_package_id = "org.sgs.example.runtime_bridge",
  ui_mode = "bridge_demo",
  create_logic = function(game) return ExampleBridgeLogic:new(game) end,
}

return pkg
