#pragma once
#include "gui/menu_item/selection.h"
#include "gui/ui/sound_editor.h"
#include "processing/sound/sound.h"

namespace deluge::gui::menu_item::osc {
/// Plaits FM quality, per sound: High = original 4x oversampling, Eco = 2x (about half the FM cost, softer top end).
class PlaitsQuality final : public Selection {
	int oscillator_;

public:
	explicit PlaitsQuality(int oscillator) : Selection(l10n::String::STRING_FOR_TYPE), oscillator_(oscillator) {}
	[[nodiscard]] std::string_view getName() const override { return "Quality"; }
	[[nodiscard]] std::string_view getTitle() const override { return "Plaits FM Quality"; }
	bool isRelevant(ModControllableAudio* mc, int32_t) const override {
		auto* sound = static_cast<Sound*>(mc);
		return sound->getSynthMode() == SynthMode::SUBTRACTIVE && isPlaits(sound->sources[oscillator_].oscType);
	}
	void readCurrentValue() override { setValue(soundEditor.currentSound->plaitsEco ? 1 : 0); }
	void writeCurrentValue() override { soundEditor.currentSound->plaitsEco = getValue() != 0; }
	deluge::vector<std::string_view> getOptions(OptType) override { return {"High", "Eco"}; }
};
} // namespace deluge::gui::menu_item::osc
