from PIL import Image, ImageDraw, ImageFont

TERMINAL_LOGS = False

# Colour values
RGBA_TRANSPARENT = (0, 0, 0, 0)
RGBA_BACKGROUND  = (255, 255, 255, 255)
RGBA_TEXT        = (0, 0, 0, 255)

def calculate_box_to_crop_out_whitespace_from_img(img, margin = 1, debug = False) :
	
	# Removes most unnecessary pixels (whitespace) from image
	# Finds the x coordinate of the leftmost and rightmost pixel
	# Finds the y coordinate of the topmost and bottommost pixel

	# Loads pixel map
	img_w, img_h  = img.size
	img_pixel_map = img.load()

	left   = img_w # Moves right
	top    = img_h # Moves down
	right  = 0     # Moves left
	bottom = 0     # Moves up

	# Iterates through every pixel
	for x in range(img_w) :
		for y in range(img_h) :
			
			# Not whitespace
			if (img_pixel_map[x, y] not in [RGBA_TRANSPARENT, RGBA_BACKGROUND]) and (x not in [0, img_w - (margin + 1)]) and (y not in [0, img_h - (margin + 1)]) :

				# ±1 because current pixel is not a whitespace
				# Hence cropping at x instead of (x ± 1) will remove part of the character

				if x < left :
					left = x - 1

				if x > right :
					right = x + 1

				if y < top :
					top = y - 1

				if y > bottom :
					bottom = y + 1

	# Keeping some whitespace for safety
	if left != 0 :
		left = left - margin

	if top != 0 :
		top = top - margin

	if right != (img_w - (margin + 1)) :
		right = right + margin

	if bottom != (img_h - (margin + 1)) :
		bottom = bottom + margin

	if debug :
		print(f"Box          = {(left, top, right, bottom)}\nMargin added = {margin}\n")

	return (left, top, right, bottom)

def calculate_wh_of_rendered_text(text, font, anchor = None, debug = False) :

	# Anchor is dependent on font being used

	# This image is a buffer
	render_text_on = Image.new("RGBA", (0, 0), RGBA_TRANSPARENT)
	draw_img     = ImageDraw.Draw(render_text_on)

	# Gets text bounding box
	# ... = (left, top, right, bottom)
	text_bbox = draw_img.textbbox(xy = (0, 0), text = text, font = font, anchor = anchor)

	# Calculates width and height
	text_w = text_bbox[2] - text_bbox[0]
	text_h = text_bbox[3] - text_bbox[1]

	# Font tries to draw character taking an equal amount of space (pixels) above and below baseline
	# i.e. Half of the character is above the baseline and half of the character is below the baseline

	# The offset shifts the character from (0, 0) to (left, top)
	# The character then satisfies the half above and half below baseline condition

	# Assuming that the text anchor is "mm"

	left = text_bbox[0] 
	top  = text_bbox[1]

	# Releases memory
	render_text_on.close()

	if debug :
		print(f"Text          = {text}\nBounding box  = {text_bbox}\nWidth, Height = {text_w, text_h}\nLeft, Top     = {left, top}\n")

	return (text_w, text_h, left, top)

class ArabicWord :

	# Arabic characters usually have UTF-8 encoding
	ENCODING = "utf-8"

	# The usual nature/bias of respective vowels

	# Hard-coded because I don't think that there's a way to know where the vowel will be pasted
	# Plus, this maybe can be hard-coded
	# Since vowels stay rather constant in the language

	VOWELS_UP   = ['َ', 'ْ', 'ُ', 'ٌ', 'ً', 'ّ']
	VOWELS_DOWN = ['ِ', 'ٍ']

	def __init__(self, word_string, font_path = None, font_size = 12, specific_vowel_offset = {}, debug = False) :
		
		self.word_string = word_string
		self.__debug     = debug

		# Init PIL font
		self.font      = ImageFont.truetype(font_path, font_size)
		self.font_size = font_size

		# Creates the image of the arabic word by calling methods

		# Seperates alphabets and vowels (tokenizes word)
		self.tokenize_word()

		# Calculates width and height of each alphabet
		# Calculates where each alphabet will be drawn

		# These values won't be used to draw alphabets
		# But to calculate where to paste images of vowels

		self.calculate_xy_and_wh_of_each_alphabet()

		# Creates images for each different vowels
		self.create_img_of_each_different_vowels()

		# Adds a small gap in between vowels and alphabets
		alphabet_vowel_gap_y = int(0.1 * self.font_size)

		# Calculates where to paste images of vowels (i.e. (left, top))
		self.calculate_xy_of_each_vowel_dependent_of_alphabet(
			alphabet_vowel_gap_y = alphabet_vowel_gap_y
			)

		# Adjusts the xy (left, top) of specific vowels
		for i, vowels_for_this_alphabet in enumerate(self.vowels_xy) :
			for j, xy in enumerate(vowels_for_this_alphabet) :
				this_vowel = self.vowels[i][j]

				# Vowel has specific additional offset
				if this_vowel in specific_vowel_offset :
					self.vowels_xy[i][j] = (xy[0] + specific_vowel_offset[this_vowel][0], xy[1] + specific_vowel_offset[this_vowel][1])

		# Some values in vowels_xy are less than 0
		# Then every xy (alphabets and vowels) will be shifted down by the smallest value (< 0)
		# Typically, only y coordinates can be less than 0

		vowels_y_less_than_zero = []

		for i in self.vowels_xy :
			for j in i :
				
				# Goes outside of bounding box
				if j[1] < 0 :
					vowels_y_less_than_zero.append(j[1])

		if vowels_y_less_than_zero :
			self.shift_y_by = abs(min(vowels_y_less_than_zero)) # | - y | = + y

		# No need to shift
		else :
			self.shift_y_by = 0

		# Adjusts xy of each alphabet

		if self.__debug :
			print(f"----------\n\nOffsetting all alphabets by {0, self.shift_y_by}\nOffsetting all vowels by {0, self.shift_y_by}\n")

		for i, xy in enumerate(self.alphabets_xy) :
			self.alphabets_xy[i] = (xy[0], xy[1] + self.shift_y_by)

			if self.__debug :
				print(f"Alphabet     = {self.alphabets[i]}\nShifted x, y = {self.alphabets_xy[i]}\n")

		# Adjusts xy of each vowel
		for i, vowels_for_this_alphabet in enumerate(self.vowels_xy) :
			for j, xy in enumerate(vowels_for_this_alphabet) :
				self.vowels_xy[i][j] = (xy[0], xy[1] + self.shift_y_by)

				if self.__debug :
					print(f"Vowel        = {self.vowels[i][j]} (for alphabet = {self.alphabets[i]})\nShifted x, y = {self.vowels_xy[i][j]}\n")

		# Calculates the total width that the image should take
		word_img_w = self.alphabets_xy[-1][0] + self.alphabets_unique_wh[self.alphabets[-1]][0]

		# Calculates the total height that the image should take
		# Finds the lowest y value (top + height) between vowels and alphabets

		# These vowels are normally drawn at the very bottom
		vowels_bottom_max = 0

		if ('ِ' in self.word_string) or ('ٍ' in self.word_string) :
			
			# Finds vowel with lowest y value (= max y)
			vowels_bottom = []

			for i, vowels_for_this_alphabet in enumerate(self.vowels) :
				for j, v in enumerate(vowels_for_this_alphabet) :
					
					# Adds top and height
					vowels_bottom.append(self.vowels_xy[i][j][1] + self.vowels_unique_img[v].size[1])

			vowels_bottom_max = max(vowels_bottom)

		# In case an alphabet goes lower than vowels
			
		# Finds alphabet with lowest y value (= max y)
		alphabets_bottom = []

		for i, a in enumerate(self.alphabets) :

			# Adds top and height
			alphabets_bottom.append(self.alphabets_xy[i][1] + self.alphabets_unique_wh[a][3] + self.alphabets_unique_wh[a][1])

		alphabets_bottom_max = max(alphabets_bottom)

		# Finds max y (bottommost character) between vowels and alphabets
		word_img_h = max([alphabets_bottom_max, vowels_bottom_max])

		# Increases total height as a safety
		word_img_h = int(1.2 * word_img_h)

		if self.__debug :
			print(f"----------\nCreating Word Image\n\nWidth, Height = {word_img_w, word_img_h}\n")

		# Creates image
		word_img = Image.new("RGBA", (word_img_w, word_img_h), RGBA_BACKGROUND)
		draw_img = ImageDraw.Draw(word_img)

		# Draws alphabets
		draw_img.text(
			xy   = self.alphabets_xy[0],
			text = "".join(i for i in self.alphabets),
			font = self.font,
			fill = RGBA_TEXT
			)

		# Pastes vowels
		for i, vowels_for_this_alphabet in enumerate(self.vowels) :
			for j, v in enumerate(vowels_for_this_alphabet)  :
				word_img.paste(self.vowels_unique_img[v], self.vowels_xy[i][j], mask = self.vowels_unique_img[v])

		self.word_img = word_img

		# Determines baseline of image of the word
		self.determine_baseline_of_word_img()

	def tokenize_word(self) :

		if self.__debug :
			print(f"----------\nTokenizing Word\n")

		# Seperates alphabets and vowels in word
		# Alphabets can have more than one vowel associated to them (2 max)

		self.alphabets = []
		self.vowels    = []

		# Stores vowels corresponding to the current alphabet
		# i.e. vowels_for_alphabets[-1] throughout iteration
		vowels_for_this_alphabet = []

		for i in self.word_string :

			# Vowel
			# Arabic vowels unicode values usually start with b'\xd9\...'
			if str(i.encode(ArabicWord.ENCODING))[3 : 6] in ["xd9"] :
				vowels_for_this_alphabet.append(i)

			# Alphabet
			else :
				self.alphabets.append(i)
				self.vowels.append(vowels_for_this_alphabet)

				# Resets for next alphabet
				vowels_for_this_alphabet = []

		if self.__debug :

			# Removes [] from vowels
			print(f"Word has {len(self.alphabets)} alphabets and {len([i for i in self.vowels if i])} vowels\n")

	def calculate_xy_and_wh_of_each_alphabet(self, offset_x = 0, offset_y = 0) :
		
		if self.__debug :
			print(f"----------\nCalculating Alphabets XY\n")

		# Offsets each alphabet's x by a certain amount
		# So that alphabet/word doesn't start exactly on edge of image
		if not offset_x :
			offset_x = int(0.1 * self.font_size)

		# Identifies each unique alphabet
		alphabets_unique = []
		
		for i in self.alphabets :

			# Unique alphabet
			if i not in alphabets_unique :
				alphabets_unique.append(i)

		if self.__debug :
			print(f"Word has {len(alphabets_unique)} different unique alphabets\n")

		# Calculates the width and height of each alphabet when drawn
		self.alphabets_unique_wh = {}

		for i in alphabets_unique :
			self.alphabets_unique_wh[i] = calculate_wh_of_rendered_text(text = i, font = self.font, debug = self.__debug)

		# Calculates where each alphabet will be drawn
		# i.e. (left, top)

		# When alphabet is drawn at (0, 0), for example
		# The actual alphabet (no whitespace) is drawn at (0 + left, 0 + top)
		# But the actual coordinate passed as parameters for xy is (0, 0) instead of (0 + left, 0 + top)
		
		self.alphabets_xy = []

		for i, a in enumerate(self.alphabets) :
			
			# Calculates the sum of the width that the alphabets before this one takes (when joined together)
			a_x = offset_x + (calculate_wh_of_rendered_text(text = "".join(j for j in self.alphabets[:i]), font = self.font, debug = self.__debug))[0]

			# Y will usually be constant for all alphabets
			# Y will later be changed depending on what vowels are pasted on top of alphabets and the height that they occupy
			a_y = offset_y

			self.alphabets_xy.append((a_x, a_y))

			if self.__debug :
				print(f"Alphabet      = {a}\nWidth, Height = {self.alphabets_unique_wh[a][0], self.alphabets_unique_wh[a][1]}\nx, y          = {a_x, a_y}\n")

		# Note that these values won't be used to draw alphabets
		# Because there may be cases where alphabets won't be properly joined together (if these values are used)
		# But these values will be used to calculate values for vowels and such

	def create_img_of_each_different_vowels(self, anchor = None) :
		
		if self.__debug :
			print(f"----------\nCreating Vowel Images\n")

		# Identifies each unique vowels
		vowels_unique = []

		for i in self.vowels :

			# Variable i is a list of vowels
			for j in i :

				# Unique vowel
				if j not in vowels_unique :
					vowels_unique.append(j)
		
		if self.__debug :
			print(f"Word has {len(vowels_unique)} different unique vowels\n")

		# Processes each unique vowel
		self.vowels_unique_img = {}

		for i in vowels_unique :
			
			# Calculates the width and height of each vowel when drawn
			text_w, text_h, left, top = calculate_wh_of_rendered_text(text = i, font = self.font, anchor = anchor, debug = self.__debug)

			# Creates images for each unique vowel
			vowel_img = Image.new("RGBA", (text_w, text_h), RGBA_TRANSPARENT)
			draw_img  = ImageDraw.Draw(vowel_img)

			# Draws character with an offset

			# Shift character from (left, top) to (0, 0)
			# Since the width and height of the image = the width and height of the character,
			# An image of only the character is created with minimal whitespace

			# This shift works well for alphabets but not so much for vowels
			# Because vowels have a lot of whitespace in the character/unicode itself

			draw_img.text(
				xy   = (- left, - top),
				text = i,
				font = self.font,
				fill = RGBA_TEXT
				)

			if self.__debug :
				print(f"Creating image of text\nText          = {i}\nWidth, Height = {text_w, text_h}\nx, y          = {- left, - top}\n")

			# Images of vowels are cropped to remove whitespace
			# Because some fonts draw vowels with whitespace and others without
			# The images are thus cropped as a standard

			# Crops image of vowel
			self.vowels_unique_img[i] = vowel_img.crop(box = calculate_box_to_crop_out_whitespace_from_img(img = vowel_img, debug = self.__debug))

	def calculate_xy_of_each_vowel_dependent_of_alphabet(self, alphabet_vowel_gap_y) :

		if self.__debug :
			print(f"----------\nCalculating Vowels XY\n")

		# Calculates where each vowel will be drawn
		# i.e. (left, top)

		self.vowels_xy = []

		# Also adds a small gap in between vowels and alphabets (= alphabet_vowel_gap_y)

		for i, vowels_for_this_alphabet in enumerate(self.vowels) :
			this_alphabet = self.alphabets[i]

			# Naming things is hard, alright!?
			xy_for_these_vowels_for_this_alphabet = []

			# xy where the alphabet is actually drawn = (left, top)
			this_alphabet_actual_wh_xy = self.alphabets_unique_wh[this_alphabet]

			this_alphabet_actual_left = self.alphabets_xy[i][0] + this_alphabet_actual_wh_xy[2]
			this_alphabet_actual_top  = self.alphabets_xy[i][1] + this_alphabet_actual_wh_xy[3]

			for j, v in enumerate(vowels_for_this_alphabet) :
				
				# Specific case scenarios
				if (this_alphabet in ['ﻷ', 'ﻵ']) and (len(vowels_for_this_alphabet) == 1) :
					
					# Places vowel as much right as possible above the character
					# Because 'ﻻ' sometimes has characters above the right side but are considered as being part of the alphabet and not a vowel
					v_x = (this_alphabet_actual_left + this_alphabet_actual_wh_xy[0]) - self.vowels_unique_img[v].size[0]


				# 'ﻻ' is a special case
				# There are 2 vowels that will be placed above 'ﻻ'
				elif (this_alphabet in ['ﻻ', 'ﻷ', 'ﻵ']) and (len(vowels_for_this_alphabet) > 1) :
					
					# Vowels will be placed next to each other

					# First vowel (leftmost vowel)
					if j == 0 :
						v_x = this_alphabet_actual_left

					# Second vowel (rightmost vowel)
					if j == 1 :
						v_x = (this_alphabet_actual_left + this_alphabet_actual_wh_xy[0]) - self.vowels_unique_img[v].size[0]

				# For other alphabets
				# But also if alphabet is 'ﻻ' and has only one vowel associated to it
				else :

					# Centers vowel above/below alphabet on x-axis
					# = A_Left + ((A_Width - V_Width) // 2)
					v_x = this_alphabet_actual_left + ((this_alphabet_actual_wh_xy[0] - self.vowels_unique_img[v].size[0]) // 2)

				# Calculates y coordinate (top)

				# If an alphabet has more than one vowels,
				# Vowels are next to each other when drawn
				# i.e. Both vowels are drawn above the alphabet

				if (v in ArabicWord.VOWELS_UP) : # or (len(vowels_for_this_alphabet) > 1) :
					
					# An alphabet may have one or two vowels drawn above it

					# Places vowel above alphabet (- to shift vowel's y up)
					# = A_Top - V_Height

					v_y = this_alphabet_actual_top - (self.vowels_unique_img[v].size[1] + alphabet_vowel_gap_y)

					# There is another vowel for this alphabet
					if (len(vowels_for_this_alphabet) > 1) and (j == 0) :
						next_v = vowels_for_this_alphabet[j + 1]

						if next_v in ['ّ'] :

							# Shifts this vowel above next vowel
							v_y = v_y - (self.vowels_unique_img[next_v].size[1] + alphabet_vowel_gap_y)

				elif v in ArabicWord.VOWELS_DOWN :
					
					# There will normally be only one vowel down

					# Places vowel below alphabet (+ to shift vowel's y down)
					# = A_Top + A_Height

					v_y = this_alphabet_actual_top + this_alphabet_actual_wh_xy[1] + alphabet_vowel_gap_y

				# Adjusting y value (top) for specific case scenarios
				if (this_alphabet in ['ﻻ', 'ﻷ', 'ﻵ']) :

					# Shifts the vowel down
					v_y = v_y + int(0.7 * self.vowels_unique_img[v].size[1])

				if self.__debug :
					print(f"Vowel         = {v} (for alphabet = {this_alphabet})\nWidth, Height = {self.vowels_unique_img[v].size}\nx, y          = {v_x, v_y}\n")

				xy_for_these_vowels_for_this_alphabet.append((v_x, v_y))

			self.vowels_xy.append(xy_for_these_vowels_for_this_alphabet)

		# Note that the images of vowels will be pasted above/below alphabets instead of drawing them with the font
		# So the (left, top) situation that comes when drawing the alphabets with the fonts won't be applicable here

	def determine_baseline_of_word_img(self) :
		
		if self.__debug :
			print(f"----------\nDetermining Baseline\n")

		# Evaluates the bounding box of a box that intersects the bounding box of all alphabets in the image of the word
		# This is being called as the "baseline"
		# i.e. The line of a copybook on which text is written 

		# This will help when pasting images of words together to form the image of a phrase
		# This will help correctly align the images of the words

		# Searching for only the topmost and bottommost values

		# Note that self.alphabets_unique_wh holds tuples containing values for:
		# (width, height, left, top)

		# Topmost value = alphabet with the lowest top (max y value)
		baseline_top = max([self.alphabets_unique_wh[a][3] for i, a in enumerate(self.alphabets)]) + self.shift_y_by

		# Bottommost value = alphabet with the highest bottom (min y value)
		baseline_bottom = min([(self.alphabets_unique_wh[a][3] + self.alphabets_unique_wh[a][1]) for i, a in enumerate(self.alphabets)]) + self.shift_y_by

		# Leftmost and rightmost values are given by the width of the image of the word
		self.baseline = (0, baseline_top, self.word_img.size[0] - 1, baseline_bottom)

		if self.__debug :
			print(f"Baseline = {self.baseline}\n")

	def show_bounding_boxes_in_img(self) :

		if self.__debug :
			print(f"----------\nCreating Debug Image\n")

		# Mainly for testing and debugging

		# Doesn't directly do <debug_img = self.word_img>
		# Because of inheritance, ...
		
		# Creates a copy of self.word_img
		debug_img = Image.new("RGBA", self.word_img.size,RGBA_BACKGROUND)
		debug_img.paste(self.word_img, (0, 0), mask = self.word_img)

		draw_img = ImageDraw.Draw(debug_img)

		# Draws boxes to show the bounding box of each vowel/alphabet
		# Categorises bounding boxes by using different colours

		# Draws bounding boxes for each alphabet (red)
		for i, xy in enumerate(self.alphabets_xy) :
			this_alphabet = self.alphabets[i]
			
			left   = xy[0] + self.alphabets_unique_wh[this_alphabet][2]
			top    = xy[1] + self.alphabets_unique_wh[this_alphabet][3]
			right  = left  + self.alphabets_unique_wh[this_alphabet][0]
			bottom = top   + self.alphabets_unique_wh[this_alphabet][1]

			draw_img.rectangle(
				xy      = (left, top, right, bottom),
				fill    = None,
				outline = (255, 0, 0, 255),
				width   = 1
				)

		# Draws bounding boxes for each vowel (blue)
		for i, vowels_for_this_alphabet in enumerate(self.vowels_xy) :
			for j, xy in enumerate(vowels_for_this_alphabet) :
				this_vowel = self.vowels[i][j]
				vowel_bbox = (xy[0], xy[1], xy[0] + self.vowels_unique_img[this_vowel].size[0], xy[1] + self.vowels_unique_img[this_vowel].size[1])

				draw_img.rectangle(
					xy      = vowel_bbox,
					fill    = None,
					outline = (0, 0, 255, 255),
					width   = 1
					)

		# Draws the bounding box of the baseline (green)
		draw_img.rectangle(
			xy      = self.baseline,
			fill    = None,
			outline = (0, 255, 0, 255),
			width   = 1
			)

		self.debug_img = debug_img

def create_img_of_sentence(list_of_word_strings, font_path, font_size = 12, create_debug_img = False, debug = False) :

	# Note that each string in list_of_word_strings should have already been correctly shaped
	
	# Creating image of a sentence/phrase by pasting images of words together
	arabic_word_obj = []

	for i in list_of_word_strings :

		# Inits ArabicWord object
		arabic_word_obj.append(
			ArabicWord(
				word_string = i,
				font_path   = font_path,
				font_size   = font_size,
				debug       = debug
				)
			)

		if create_debug_img :
			arabic_word_obj[-1].show_bounding_boxes_in_img()
	
	# Extracts all the widths and heights seperately for calculations later on
	all_obj_w = [i.word_img.size[0] for i in arabic_word_obj]
	all_obj_h = [i.word_img.size[1] for i in arabic_word_obj]

	# Finds the baseline of the tallest word
	tallest_word    = arabic_word_obj[all_obj_h.index(max(all_obj_h))]
	lowest_baseline = tallest_word.baseline[3]

	# The image of the word is slightly bigger than the actual space (width and height) occupied by the word in the image
	# Since the baseline for every word is determined by the tallest word
	# Words with alphabets that are drawn below the baseline (i.e 'ﻦ', 'ﻲ') will be favoured over others (i.e 'ﻈ')

	# Baseline is thus increased by a tiny percentage
	# So that words that have tall alphabets (going up) don't have their vowels cut (most likely when they have 2)

	lowest_baseline = int(1.1 * lowest_baseline)

	# Finds the width taken by a " "
	space_w = calculate_wh_of_rendered_text(text = " ", font = ImageFont.truetype(font_path, font_size))[0]

	# Creates image of sentence
	sentence_w   = sum(all_obj_w) + (len(arabic_word_obj) * space_w)
	sentence_h   = max(all_obj_h)
	sentence_img = Image.new("RGBA", (sentence_w, sentence_h), RGBA_BACKGROUND)

	# Pastes images of words together
	for i, obj in enumerate(arabic_word_obj) :
		obj_x = sum(all_obj_w[:i]) + (len(all_obj_w[:i]) * space_w)

		# Shifts image on y-axis to match/align baseline
		obj_y = lowest_baseline - obj.baseline[3]

		# Uses image of word with bounding boxes drawn
		if create_debug_img :
			img_to_paste = obj.debug_img

		else :
			img_to_paste = obj.word_img

		sentence_img.paste(img_to_paste, (obj_x, obj_y), mask = img_to_paste)

	return sentence_img

if __name__ == "__main__" :

	# These are prerequisites before using the class and its methods

	# Connects alphabets to each other correctly (shapes alphabets)
	import arabic_reshaper

	arabic_reshaper_config = {
		"delete_harakat"         : False,
		"shift_harakat_position" : False,
		"delete_tatweel"         : True
	}

	reshaper = arabic_reshaper.ArabicReshaper(configuration = arabic_reshaper_config)

	# Right to Left orientation
	from bidi.algorithm import get_display

	# PIL font parameters
	font_path = "path to locally installed font"
	font_size = 64

	# Correctly shapes text
	text_unshaped     = u"لَكِنَّ لَا بَدَّ أَنَّ أوْضَحَ لَكَ أَنَّ كُلُّ هَذِهِ الْأَفْكَارِ الْمَغْلُوطَةِ حَوْلَ اِسْتِنْكَارِ النَّشْوَةٌ وَتَمْجيدِ الْألَمِ نَشَّأَتٍ بِالْفِعْلِ، وَسَأَعْرُضُ لَكَ التَّفَاصِيلُ لِتَكْتَشِفٌ حَقِيقَةٌ وَأَسَاسٍ تِلْكَ السَّعَادَةً الْبَشَرِيَّةِ، فَلَا أحَدٌ يَرْفُضُ أَوْ يَكْرَهُ أَوْ يَتَجَنَّبُ الشُّعُورٌ بِالسَّعَادَةِ، وَلَكِنَّ بِفَضْلِ هَؤُلَاءِ الْأَشْخَاصِ الَّذِينَ لَا يُدْرِكُونَ بِأَنَّ السَّعَادَةً لَا بَدَّ أَنَّ نَسْتَشْعِرُهَا بِصُورَةِ أَكْثَرِ عَقْلَانِيَّةٍ وَمِنْطَقِيَّةٍ فَيَعْرُضُهُمْ هَذَا لِمُوَاجَهَةُ الظُّروفآ الْألِيمَةِ، وَأُكَرِّرُ بِأَنَّهُ لَا يُوجَدُ مَنْ يَرْغَبُ فِي الْحُبِّ وَنَيْلِ الْمَنَالِ وَيَتَلَذَّذُ بِالْآلَاَمِ، الْألَمَ هُوَ الْألَمُ وَلَكِنَّ نَتِيجَةً لِظُروفٍ مَا قَدْ تَكْمُنُ السعاده فِيمَا نَتَحَمَّلُهُ مِنْ كَدٍّ وَأُسِّيٍّ."
	text_shaped       = get_display(reshaper.reshape(text_unshaped), base_dir = "R")
	text_shaped_words = text_shaped.split(" ")

	# How to use the class and its methods

	# Inits object
	arabic_word = ArabicWord(
		word_string = text_shaped_words[45],
		font_path   = font_path,
		font_size   = font_size,
		debug       = TERMINAL_LOGS
		)

	# The image of the arabic word is created when the ArabicWord object is initialised
	# Attribute word_img is a PIL Image object
	arabic_word.word_img.show()

	# Draws bounding boxes for validation
	arabic_word.show_bounding_boxes_in_img()
	arabic_word.debug_img.show()

	# Creating image of a sentence
	sentence_img = create_img_of_sentence(
		list_of_word_strings = text_shaped_words,
		font_path            = font_path,
		font_size            = font_size,
		create_debug_img     = True,
		debug                = TERMINAL_LOGS
		)	

	sentence_img.show()