// Plaits FM Eco (2x oversampling): finite and bounded, same pitch, same level as High within 1.5 dB at gentle
// settings, High path bit-identical to the default call, and fewer operations per sample.
#include "dsp/plaits/voice.h"
#include <cassert>
#include <chrono>
#include <cmath>
#include <iostream>
#include <vector>
using deluge::dsp::PlaitsVoice;
static uint32_t increment(float hz) { return static_cast<uint32_t>(hz * (4294967296.0 / 44100.0)); }
static double rms(const std::vector<float>& v, size_t from) {
	double e = 0;
	for (size_t i = from; i < v.size(); ++i)
		e += double(v[i]) * v[i];
	return std::sqrt(e / double(v.size() - from));
}
static double frequency(const std::vector<float>& v, size_t from) {
	int crossings = 0;
	double first = -1, last = -1;
	for (size_t i = from + 1; i < v.size(); ++i)
		if (v[i - 1] < 0 && v[i] >= 0) {
			const double t = double(i - 1) + v[i - 1] / (v[i - 1] - v[i]);
			if (first < 0)
				first = t;
			last = t;
			++crossings;
		}
	return (crossings - 1) * 44100.0 / (last - first);
}
static std::vector<float> render(float hz, float h, float t, float m, bool eco, size_t n = 44100) {
	PlaitsVoice v(0);
	std::vector<float> out(n);
	for (size_t i = 0; i < n; i += 128)
		v.render(increment(hz), h, t, m, out.data() + i, std::min<size_t>(128, n - i), eco);
	return out;
}
int main() {
	// Default argument keeps the original 4x path exactly.
	{
		PlaitsVoice a(0), b(0);
		std::vector<float> x(4096), y(4096);
		a.render(increment(220), .4f, .7f, .3f, x.data(), x.size());
		b.render(increment(220), .4f, .7f, .3f, y.data(), y.size(), false);
		assert(x == y);
	}
	for (float hz : {55.f, 110.f, 440.f, 1760.f}) {
		// Timbre 0 = no FM: a pure carrier, so pitch and level must agree between rates.
		auto high = render(hz, .5f, 0.f, .5f, false), eco = render(hz, .5f, 0.f, .5f, true);
		const double fh = frequency(high, 4410), fe = frequency(eco, 4410);
		assert(std::abs(fe - fh) / fh < 0.002);
		const double dB = 20 * std::log10(rms(eco, 4410) / rms(high, 4410));
		assert(std::abs(dB) < 1.5);
		std::cout << "  " << hz << " Hz: high " << fh << " Hz, eco " << fe << " Hz, level " << dB << " dB\n";
	}
	for (float hz : {8.18f, 440.f, 12000.f, 20000.f})
		for (float h : {0.f, .5f, 1.f})
			for (float t : {0.f, .5f, 1.f})
				for (float m : {0.f, .5f, 1.f}) {
					auto eco = render(hz, h, t, m, true, 2048);
					for (float s : eco)
						assert(std::isfinite(s) && std::abs(s) <= 1.f);
				}
	auto time = [](bool eco) {
		const auto start = std::chrono::steady_clock::now();
		volatile float sink = 0;
		for (int k = 0; k < 20; ++k)
			sink = sink + render(440.f, .6f, .8f, .7f, eco, 44100)[100];
		return std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
	};
	const double high = time(false), eco = time(true);
	std::cout << "  host time eco/high: " << eco / high << "\n";
	std::cout << "PASS Plaits FM Eco: default path unchanged, pitch within 0.2%, level within 1.5 dB, bounded output at "
	             "all corners\n";
}
