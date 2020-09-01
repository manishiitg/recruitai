def get_labels(file):
    # try:
    result = []
    with open(file, "r") as myfile:
        nerTestLines = myfile.read()
        nerTestLines = nerTestLines.splitlines()

        for line in nerTestLines:
            if len(line.strip()) == 0:

                continue

            result.append(line.split("  ")[1].strip())

    return set(list(result))


def get_file_after_remove_labels(file, labels_to_remove=[]):
    newfile = "label_remove_email_dob" + file
    with open(newfile, "w") as myfile2:
        with open(file, "r") as myfile:
            nerTestLines = myfile.read()
            nerTestLines = nerTestLines.splitlines()

            for line in nerTestLines:
                if len(line.strip()) == 0:
                    myfile2.write("\n")
                else:
                    val = line.split("  ")[0].strip()
                    label = line.split("  ")[1].strip()

                    if label in labels_to_remove:
                        label = "O"

                    myfile2.write(val + "  " + label + "\n")

    myfile2.close()
    return newfile


labels = get_labels("ner-train-v2.txt")
print(labels)

filename = get_file_after_remove_labels("ner-train-v2.txt", ["Skills",'LANGUAGE'])
labels1 = get_labels(filename)
print(labels1)

filename = get_file_after_remove_labels("ner-full-v2.txt", ["Skills",'LANGUAGE'])
filename = get_file_after_remove_labels("ner-test-v2.txt", ["Skills",'LANGUAGE'])
filename = get_file_after_remove_labels("ner-dev-v2.txt", ["Skills",'LANGUAGE'])