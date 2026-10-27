#pragma once
#include "gui/menu_item/formatted_title.h"
#include "gui/menu_item/source/patched_param.h"
#include "processing/sound/sound.h"

namespace deluge::gui::menu_item::osc::source {
/// Plaits Morph. A hybrid (additive) param like Harmonics and Timbre, so an LFO, envelope or MDD Custom lane
/// can open it from any knob position.
class PlaitsMorph final : public menu_item::source::PatchedParam, public FormattedTitle {
public:
	PlaitsMorph(l10n::String name, l10n::String title_format_str, int32_t newP, uint8_t source_id)
	    : PatchedParam(name, newP, source_id), FormattedTitle(title_format_str, source_id + 1) {}

	[[nodiscard]] std::string_view getName() const override { return "Morph"; }
	[[nodiscard]] std::string_view getTitle() const override { return "Morph"; }

	bool isRelevant(ModControllableAudio* modControllable, int32_t) const override {
		const auto sound = static_cast<Sound*>(modControllable);
		return sound->getSynthMode() == SynthMode::SUBTRACTIVE && isPlaits(sound->sources[source_id_].oscType);
	}

	[[nodiscard]] RenderingStyle getRenderingStyle() const override { return SLIDER; }
};
} // namespace deluge::gui::menu_item::osc::source
