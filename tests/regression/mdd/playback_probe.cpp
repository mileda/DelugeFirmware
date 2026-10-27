#include "sequencer/mdd/controller.hpp"
#include "sequencer/mdd/held_notes.hpp"
#include <cassert>
#include <iostream>
#include <vector>
constexpr int MIDI_CHANNEL_NONE=-1,kNumExpressionDimensions=3;
enum class OutputType{SYNTH,MIDI_OUT,CV,KIT};
struct Key{int degreeOf(int n){return (n%12==0||n%12==4||n%12==7)?1:-1;}};
struct Song{Key key;int quarter=24;int getQuarterNoteLength(){return quarter;}};
Song defaultSong;Song*currentSong=&defaultSong;
struct ModelStackWithThreeMainThings{};
struct ModelStackWithTimelineCounter{Song* song;ModelStackWithThreeMainThings* addOtherTwoThingsButNoNoteRow(void*,void*){static ModelStackWithThreeMainThings s;return &s;}};
struct Sound{const void* mddClipOwner=nullptr;bool mddClipActive=false;uint8_t mddBakedSources=0;std::array<int32_t,4> v{};void setSnakeCustomValues(std::array<int32_t,4> x){v=x;}};
struct MelodicInstrument{void* activeClip=nullptr;OutputType type=OutputType::SYNTH;Sound sound;std::vector<int> events;void* toModControllable(){return &sound;}void sendNote(ModelStackWithThreeMainThings*,bool on,int note,const int16_t*,int=-1,uint8_t=64){events.push_back(on?note+1:-note-1);}std::vector<std::pair<int,int>> ccs;};
struct MIDIInstrument:MelodicInstrument{void sendMddCC(uint8_t cc,uint8_t v){ccs.push_back({cc,v});}};
struct Clock{bool active=true;void expectEvent(){}bool isEitherClockActive(){return active;}}playbackHandler;
namespace params{constexpr int GLOBAL_MDD_CUSTOM_1=0;}
struct Patched{int getValue(int){return 0;}};struct Params{Patched p;Patched*getPatchedParamSet(){return &p;}};
struct InstrumentClip{snake::Controller mdd;snake::HeldNotes mddHeld;uint8_t mddBakedCustom=0;bool mddUsed=false;std::array<uint8_t,4> mddLastSentCC{0xFF,0xFF,0xFF,0xFF};Params paramManager;void publishMddCustom(const snake::Frame* liveFrame=nullptr);MelodicInstrument* output;int ticksTilNextNoteRowEvent=0,lastProcessedPos=0,loopLength=96,repeatCount=0,mddNormalPos=0,mddNormalRepeat=0;bool mddNormalReversed=false,currentlyPlayingReversed=false;bool inScaleMode=false,mddNoteOn=false,mddEnabled=false,mddRequested=false,mddPending=false;uint64_t mddTick=0,mddLastProcessed=UINT64_MAX,mddOffAt=0;uint8_t mddNote=60;bool isActiveOnOutput()const{return output->activeClip==this;}void requestMdd(bool);void closeMdd(ModelStackWithTimelineCounter*);void processMdd(ModelStackWithTimelineCounter*);int mddQuantize(int,Song*)const;};
int InstrumentClip::mddQuantize(int note, Song* song) const {
	if (!inScaleMode)
		return note;
	for (int d = 0; d < 12; ++d) {
		if (note - d >= 0 && song->key.degreeOf(note - d) >= 0)
			return note - d;
		if (note + d <= 127 && song->key.degreeOf(note + d) >= 0)
			return note + d;
	}
	return note;
}
void InstrumentClip::closeMdd(ModelStackWithTimelineCounter* stack) {
	if (output && output->type != OutputType::KIT) {
		auto* model = stack->addOtherTwoThingsButNoNoteRow(output->toModControllable(), &paramManager);
		mddHeld.stop(
		    [&](uint8_t pitch) { static_cast<MelodicInstrument*>(output)->sendNote(model, false, pitch, nullptr); });
	}
	else
		mddHeld = {};
	mddNoteOn = false;
	mddLastSentCC.fill(0xFF);
	if (output && output->type == OutputType::SYNTH) {
		auto* sound = static_cast<Sound*>(output->toModControllable());
		if (sound->mddClipOwner == this) {
			sound->mddClipActive = false;
			sound->mddBakedSources = 0;
			sound->mddClipOwner = nullptr;
			sound->setSnakeCustomValues({});
		}
	}
}
void InstrumentClip::processMdd(ModelStackWithTimelineCounter* stack) {
	if (!output || !isActiveOnOutput() || output->type == OutputType::KIT)
		return;
	auto* model = stack->addOtherTwoThingsButNoNoteRow(output->toModControllable(), &paramManager);
	auto* instrument = static_cast<MelodicInstrument*>(output);
	mdd.activateClock(stack->song->getQuarterNoteLength());
	auto frame = mdd.core.advance(mddTick);
	if (mddLastProcessed == mddTick)
		frame.trigger = false;
	mddLastProcessed = mddTick;
	publishMddCustom(&frame);
	if (output->type == OutputType::MIDI_OUT) {
		// Custom lanes as MIDI CC: 7-bit value, sent only when it changes.
		auto* midi = static_cast<MIDIInstrument*>(output);
		for (int i = 0; i < 4; ++i) {
			const uint8_t cc = mdd.midiCC[i];
			if (cc == snake::Controller::kNoMidiCC)
				continue;
			const uint8_t value = frame.custom[i] >> 9;
			if (value != mddLastSentCC[i]) {
				midi->sendMddCC(cc, value);
				mddLastSentCC[i] = value;
			}
		}
	}
	frame.note = mddQuantize(frame.note, stack->song);
	mddHeld.advance(
	    frame, mddTick,
	    [&](uint8_t note, uint8_t velocity) {
		    int16_t mpe[kNumExpressionDimensions]{};
		    instrument->sendNote(model, true, note, mpe, MIDI_CHANNEL_NONE, velocity);
		    mddNote = note;
	    },
	    [&](uint8_t note) { instrument->sendNote(model, false, note, nullptr); });
	mddNoteOn = mddHeld.active();
}
void InstrumentClip::publishMddCustom(const snake::Frame* liveFrame) {
	if (!output || output->type != OutputType::SYNTH || !isActiveOnOutput())
		return;
	auto* sound = static_cast<Sound*>(output->toModControllable());
	if (!mddEnabled && !mddBakedCustom)
		return;
	sound->mddClipActive = true;
	sound->mddClipOwner = this;
	sound->mddBakedSources = mddEnabled ? 0 : mddBakedCustom;
	std::array<int32_t, 4> values{};
	if (mddEnabled) {
		// Reuse the frame processMdd() already evaluated for this tick.
		const snake::Frame frame = liveFrame ? *liveFrame : mdd.core.advance(mddTick);
		for (int i = 0; i < 4; ++i)
			values[i] = snake::normalizedQ31(frame.custom[i]);
	}
	else {
		for (int i = 0; i < 4; ++i)
			if (mddBakedCustom & (1u << i))
				values[i] =
				    std::max<int32_t>(0, paramManager.getPatchedParamSet()->getValue(params::GLOBAL_MDD_CUSTOM_1 + i));
	}
	sound->setSnakeCustomValues(values);
}
void InstrumentClip::requestMdd(bool enabled) {
	if (!output)
		return;
	if (output->type != OutputType::SYNTH && output->type != OutputType::MIDI_OUT && output->type != OutputType::CV)
		return;
	if (enabled) {
		mdd.activateClock(currentSong->getQuarterNoteLength());
		mddUsed = true;
	}
	else
		mdd.syncClock(currentSong->getQuarterNoteLength());
	mddRequested = enabled;
	mddPending = enabled != mddEnabled;
	ticksTilNextNoteRowEvent = 0;
	playbackHandler.expectEvent();
	if (!playbackHandler.isEitherClockActive()) {
		if (enabled && !mddEnabled) {
			mddNormalPos = lastProcessedPos;
			mddNormalRepeat = repeatCount;
			mddNormalReversed = currentlyPlayingReversed;
		}
		if (!enabled && mddEnabled) {
			lastProcessedPos = std::clamp<int32_t>(mddNormalPos, 0, loopLength - 1);
			repeatCount = mddNormalRepeat;
			currentlyPlayingReversed = mddNormalReversed;
		}
		mddEnabled = enabled;
		mddPending = false;
	}
}
int main(){
 {Song coldSong;coldSong.quarter=96;currentSong=&coldSong;InstrumentClip cold;MelodicInstrument output;cold.output=&output;output.activeClip=&cold;ModelStackWithTimelineCounter coldStack{&coldSong};cold.requestMdd(true);
 for(auto&lane:cold.mdd.core.lanes)assert(lane.ticks==24&&lane.tickDenominator==1&&cold.mdd.speedIndex(lane)==2);
 cold.mddEnabled=true;cold.processMdd(&coldStack);assert(output.events.size()==1);cold.mddTick=6;cold.processMdd(&coldStack);assert(output.events.size()==1);cold.mddTick=12;cold.processMdd(&coldStack);assert(output.events.size()==2);cold.mddTick=24;cold.processMdd(&coldStack);assert(output.events.size()==3);
 currentSong=&defaultSong;}
 InstrumentClip c;MelodicInstrument out;c.output=&out;out.activeClip=&c;Song song;ModelStackWithTimelineCounter stack{&song};c.mdd.core.lanes[3].values.fill(12345);c.requestMdd(true);assert(c.mddPending&&!c.mddEnabled);c.mddEnabled=true;c.mddPending=false;c.processMdd(&stack);assert(out.events.size()==1&&out.events[0]==61&&out.sound.mddClipActive&&out.sound.v[0]>0);c.processMdd(&stack);assert(out.events.size()==1);c.mddTick=3;c.processMdd(&stack);assert(out.events.size()==2&&out.events[1]==-61);c.mddTick=6;c.processMdd(&stack);assert(out.events.size()==3);InstrumentClip inactive;inactive.output=&out;inactive.closeMdd(&stack);assert(out.sound.mddClipActive&&out.sound.mddClipOwner==&c&&out.sound.v[0]>0);c.closeMdd(&stack);assert(out.events.size()==4&&!out.sound.mddClipActive&&out.sound.v[0]==0&&c.mddTick==6&&out.sound.mddClipOwner==nullptr);c.mddTick=12;c.mdd.core.lanes[1].values.fill(0);c.processMdd(&stack);assert(out.events.size()==4);c.inScaleMode=true;assert(c.mddQuantize(61,&song)==60);playbackHandler.active=false;c.requestMdd(false);assert(!c.mddEnabled&&!c.mddPending);c.lastProcessedPos=13;c.repeatCount=3;c.currentlyPlayingReversed=true;c.requestMdd(true);assert(c.mddEnabled&&c.mddNormalPos==13);c.lastProcessedPos=69;c.repeatCount=9;c.currentlyPlayingReversed=false;c.requestMdd(false);assert(c.lastProcessedPos==13&&c.repeatCount==3&&c.currentlyPlayingReversed);
 // MIDI clips: Custom lane 1 as CC 74, 7-bit, sent only when the step value changes; closing re-arms it.
 {playbackHandler.active=true;InstrumentClip m;MIDIInstrument midi;midi.type=OutputType::MIDI_OUT;m.output=&midi;midi.activeClip=&m;ModelStackWithTimelineCounter ms{&song};
  m.requestMdd(true);m.mddEnabled=true;m.mddPending=false;assert(m.mddUsed);m.mdd.midiCC[0]=74;
  for(int i=0;i<16;++i)m.mdd.core.lanes[3].values[i]=i<8?65535:0;
  for(uint64_t t=0;t<6*16;t+=3){m.mddTick=t;m.processMdd(&ms);}
  assert(midi.ccs.size()==2&&midi.ccs[0]==std::make_pair(74,127)&&midi.ccs[1]==std::make_pair(74,0));
  m.closeMdd(&ms);m.mddTick=0;m.mddLastProcessed=UINT64_MAX;m.processMdd(&ms);assert(midi.ccs.size()==3&&midi.ccs[2].second==127);
  assert(!midi.sound.mddClipActive);}
 std::cout<<"PASS actual InstrumentClip bridge: note-on/off, gate duration, duplicate tick, Custom output, cleanup, root/scale, deferred selection and MIDI CC lanes\n";}
